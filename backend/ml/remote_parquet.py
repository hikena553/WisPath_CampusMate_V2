"""远程 parquet 惰性读取：不下载整个数据集，只取你要用的那部分。

背景
----
HuggingFace 上的数据集多以 parquet 存放，而 parquet 是**可随机访问**的格式：
文件尾部有元数据（footer），记录了每个行组（row group）在文件中的字节偏移与长度。
因此只要用 HTTP Range 请求，就能"读元数据 -> 只下需要的行组"，无需把整个文件拉到本地。

本模块实现一个最小的 HTTP Range 文件对象，并统计**实际传输字节数**，
用来回答"能不能直接对接远程数据、不落本地"这个问题。

用法（在 backend 目录下）：
  python -m ml.remote_parquet                       # 用 AffectNet 分片做演示
  python -m ml.remote_parquet --rows 12
"""
from __future__ import annotations

import argparse
import io
import time
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

DEFAULT_URL = ("https://hf-mirror.com/datasets/deanngkl/affectnet_no_contempt/"
               "resolve/main/data/train-00000-of-00016.parquet")


class HttpRangeFile(io.RawIOBase):
    """把 HTTP Range 请求伪装成可 seek 的只读文件，并统计传输量。"""

    def __init__(self, url: str) -> None:
        self.url = url
        self.pos = 0
        self.bytes_transferred = 0
        self.requests = 0
        self.size = self._probe_size()

    def _probe_size(self) -> int:
        req = urllib.request.Request(self.url, headers={"User-Agent": UA, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            cr = r.headers.get("Content-Range", "")
            self.bytes_transferred += 1
            self.requests += 1
            r.read()
        if "/" in cr:
            return int(cr.split("/")[-1])
        raise SystemExit(f"服务端未返回 Content-Range，无法随机访问：{cr!r}")

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        if n <= 0 or self.pos >= self.size:
            return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(
            self.url, headers={"User-Agent": UA, "Range": f"bytes={self.pos}-{end}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                break
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(1.5)
        self.bytes_transferred += len(data)
        self.requests += 1
        self.pos += len(data)
        return data

    def readinto(self, b) -> int:  # type: ignore[override]
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def main() -> None:
    ap = argparse.ArgumentParser(description="远程 parquet 惰性读取演示")
    ap.add_argument("--url", type=str, default=DEFAULT_URL)
    ap.add_argument("--rows", type=int, default=8, help="要取多少行样本")
    args = ap.parse_args()

    import pyarrow.parquet as pq

    print(f"目标: {args.url}", flush=True)
    f = HttpRangeFile(args.url)
    print(f"文件总大小: {f.size / 1e6:.1f} MB（未下载）", flush=True)
    print(f"  探测大小已传输: {f.bytes_transferred} 字节 / {f.requests} 次请求", flush=True)

    t0 = time.time()
    pf = pq.ParquetFile(f)
    print(f"读取元数据后: 传输 {f.bytes_transferred / 1e6:.2f} MB / {f.requests} 次请求", flush=True)
    print(f"  行数={pf.metadata.num_rows}  行组数={pf.metadata.num_row_groups}  "
          f"列={pf.schema_arrow.names}", flush=True)

    # 只读第 0 个行组，取前 N 行
    rg = pf.metadata.row_group(0)
    print(f"  第 0 个行组: {rg.num_rows} 行, {rg.total_byte_size / 1e6:.2f} MB 未压缩", flush=True)

    table = pf.read_row_group(0)
    print(f"读入行组后: 传输 {f.bytes_transferred / 1e6:.2f} MB / {f.requests} 次请求", flush=True)

    imgs = table.column("image").to_pylist()[: args.rows]
    labs = table.column("label").to_pylist()[: args.rows]
    total_mb = f.size / 1e6
    got_mb = f.bytes_transferred / 1e6
    print(f"\n取到 {len(imgs)} 个样本，标签={labs}", flush=True)
    if imgs and isinstance(imgs[0], dict) and imgs[0].get("bytes"):
        from PIL import Image
        im = Image.open(io.BytesIO(imgs[0]["bytes"]))
        print(f"  首图: {im.size} {im.mode}, {len(imgs[0]['bytes'])} 字节", flush=True)

    print(f"\n耗时 {time.time() - t0:.1f}s", flush=True)
    print(f"结论: 整个文件 {total_mb:.1f} MB，实际只传输 {got_mb:.2f} MB"
          f"（占 {got_mb / total_mb * 100:.1f}%），全程未落地", flush=True)
    out = Path(__file__).resolve().parent / "runs" / "remote_parquet_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f'{{"url": "{args.url}", "file_mb": {total_mb:.2f}, "transferred_mb": {got_mb:.3f}, '
        f'"requests": {f.requests}, "rows_read": {len(imgs)}}}', encoding="utf-8")
    print(f"已保存: {out}", flush=True)


if __name__ == "__main__":
    main()