# -*- coding: utf-8 -*-
"""
青果教务系统（KINGOSOFT）登录参数 DES 加密的纯 Python 实现（零第三方依赖）。

协议与 jkingo.des.js（青果前端加密脚本）逐函数对齐：
将数据按 4 字符分块，每块按 UTF-16 码元逐位取 64 位，DES 单密钥迭代加密，
密钥同样按 4 字符切块后逐块迭代；最终输出大写 hex 并 base64 编码。

对外接口：
    KingoDES.encrypt(data: str, des_key: str) -> str   # 返回 base64 编码密文
"""

import base64

__all__ = ["KingoDES"]


def _str_to_bt(s: str) -> list:
    """将不超过 4 个字符的字符串转为 64 位 bit 数组（UTF-16 码元逐位读取，不足补 0）。"""
    bt = [0] * 64
    leng = len(s)
    for i in range(min(leng, 4)):
        code = ord(s[i])
        for j in range(16):
            bt[16 * i + j] = (code >> (15 - j)) & 1
    return bt


def _get_key_bytes(key: str) -> list:
    """JS getKeyBytes：密钥按 4 字符切块，每块转 64 bit。"""
    key_bytes = []
    leng = len(key)
    for i in range(0, leng, 4):
        key_bytes.append(_str_to_bt(key[i:i + 4]))
    return key_bytes


def _init_permute(original: list) -> list:
    """初始置换 IP（JS 循环写法等价于标准 IP 表）。"""
    ip = [0] * 64
    m, n = 1, 0
    for i in range(4):
        k = 0
        for j in range(7, -1, -1):
            ip[i * 8 + k] = original[j * 8 + m]
            ip[i * 8 + k + 32] = original[j * 8 + n]
            k += 1
        m += 2
        n += 2
    return ip


def _expand_permute(right: list) -> list:
    """扩展置换 E：32 -> 48 bit。"""
    ep = [0] * 48
    for i in range(8):
        ep[i * 6 + 0] = right[31] if i == 0 else right[i * 4 - 1]
        ep[i * 6 + 1] = right[i * 4 + 0]
        ep[i * 6 + 2] = right[i * 4 + 1]
        ep[i * 6 + 3] = right[i * 4 + 2]
        ep[i * 6 + 4] = right[i * 4 + 3]
        ep[i * 6 + 5] = right[0] if i == 7 else right[i * 4 + 4]
    return ep


def _xor(a: list, b: list) -> list:
    return [x ^ y for x, y in zip(a, b)]


# 标准 DES 8 个 S 盒
_SBOXES = (
    ((14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7),
     (0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8),
     (4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0),
     (15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13)),
    ((15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10),
     (3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5),
     (0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15),
     (13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9)),
    ((10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8),
     (13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1),
     (13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7),
     (1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12)),
    ((7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15),
     (13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9),
     (10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4),
     (3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14)),
    ((2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9),
     (14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6),
     (4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14),
     (11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3)),
    ((12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11),
     (10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8),
     (9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6),
     (4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13)),
    ((4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1),
     (13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6),
     (1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2),
     (6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12)),
    ((13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7),
     (1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2),
     (7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8),
     (2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11)),
)


def _s_box_permute(xor_byte: list) -> list:
    """S 盒代换：48 -> 32 bit。"""
    out = [0] * 32
    for m in range(8):
        row = xor_byte[m * 6 + 0] * 2 + xor_byte[m * 6 + 5]
        col = (xor_byte[m * 6 + 1] * 8 + xor_byte[m * 6 + 2] * 4 +
               xor_byte[m * 6 + 3] * 2 + xor_byte[m * 6 + 4])
        val = _SBOXES[m][row][col]
        out[m * 4 + 0] = (val >> 3) & 1
        out[m * 4 + 1] = (val >> 2) & 1
        out[m * 4 + 2] = (val >> 1) & 1
        out[m * 4 + 3] = val & 1
    return out


# P 置换表
_P_SOURCE = (15, 6, 19, 20, 28, 11, 27, 16, 0, 14, 22, 25, 4, 17, 30, 9,
             1, 7, 23, 13, 31, 26, 2, 8, 18, 12, 29, 5, 21, 10, 3, 24)


def _p_permute(s_box_byte: list) -> list:
    return [s_box_byte[src] for src in _P_SOURCE]


# 逆初始置换 FP
_FP_SOURCE = (39, 7, 47, 15, 55, 23, 63, 31,
              38, 6, 46, 14, 54, 22, 62, 30,
              37, 5, 45, 13, 53, 21, 61, 29,
              36, 4, 44, 12, 52, 20, 60, 28,
              35, 3, 43, 11, 51, 19, 59, 27,
              34, 2, 42, 10, 50, 18, 58, 26,
              33, 1, 41, 9, 49, 17, 57, 25,
              32, 0, 40, 8, 48, 16, 56, 24)


def _finally_permute(end_byte: list) -> list:
    return [end_byte[src] for src in _FP_SOURCE]


# 每轮循环左移位数
_KEY_LOOP = (1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1)

# 压缩置换 PC-2：56 -> 48 bit（0 起始下标）
_PC2 = (13, 16, 10, 23, 0, 4, 2, 27, 14, 5, 20, 9, 22, 18, 11, 3,
        25, 7, 15, 6, 26, 19, 12, 1, 40, 51, 30, 36, 46, 54, 29, 39,
        50, 44, 32, 47, 43, 48, 38, 55, 33, 52, 45, 41, 49, 35, 28, 31)


def _generate_keys(key_byte: list) -> list:
    """生成 16 个 48-bit 子密钥。

    与 JS generateKeys 一致：先做 PC-1（按列取位 7x8 -> 56 bit），
    再按 _KEY_LOOP 循环左移后做 PC-2 压缩。
    """
    key = [0] * 56
    for i in range(7):
        for j in range(8):
            key[i * 8 + j] = key_byte[8 * (7 - j) + i]
    keys = []
    for i in range(16):
        for _ in range(_KEY_LOOP[i]):
            left_head = key[0]
            right_head = key[28]
            for k in range(27):
                key[k] = key[k + 1]
                key[28 + k] = key[29 + k]
            key[27] = left_head
            key[55] = right_head
        keys.append([key[idx] for idx in _PC2])
    return keys


def _enc(data_byte: list, key_byte: list) -> list:
    """标准 DES 单块加密（Feistel 16 轮）。"""
    keys = _generate_keys(key_byte)
    ip = _init_permute(data_byte)
    left = ip[:32]
    right = ip[32:]
    for i in range(16):
        new_left = right
        new_right = _xor(
            _p_permute(_s_box_permute(_xor(_expand_permute(right), keys[i]))),
            left,
        )
        left = new_left
        right = new_right
    return _finally_permute(right + left)


_HEX = "0123456789ABCDEF"


def _bt64_to_hex(bit_array: list) -> str:
    """64 bit -> 16 个大写 hex 字符。"""
    return "".join(
        _HEX[bit_array[i * 4] * 8 + bit_array[i * 4 + 1] * 4 +
             bit_array[i * 4 + 2] * 2 + bit_array[i * 4 + 3]]
        for i in range(16)
    )


def kingo_str_enc(data: str, key: str, second_key: str = None,
                  third_key: str = None) -> str:
    """青果 strEnc：数据按 4 字符分块，依次用第一/二/三组密钥迭代加密。

    Args:
        data: 明文字符串
        key: 主密钥
        second_key / third_key: 可选第二、第三段密钥（教务登录仅用主密钥）
    Returns:
        拼接后的大写 hex 密文
    """
    enc_parts = []
    first_key_bt = _get_key_bytes(key) if key else None
    second_key_bt = _get_key_bytes(second_key) if second_key else None
    third_key_bt = _get_key_bytes(third_key) if third_key else None

    def _process(chunk: str) -> None:
        temp_bt = _str_to_bt(chunk)
        for kb in first_key_bt:
            temp_bt = _enc(temp_bt, kb)
        if second_key_bt is not None:
            for kb in second_key_bt:
                temp_bt = _enc(temp_bt, kb)
        if third_key_bt is not None:
            for kb in third_key_bt:
                temp_bt = _enc(temp_bt, kb)
        enc_parts.append(_bt64_to_hex(temp_bt))

    leng = len(data or "")
    if leng > 0:
        if leng < 4:
            _process(data)
        else:
            iterator = leng // 4
            for i in range(iterator):
                _process(data[i * 4:i * 4 + 4])
            if leng % 4 > 0:
                _process(data[iterator * 4:])
    return "".join(enc_parts)


class KingoDES:
    """对外统一入口，与青果前端 jkingo.des 的 KingoDES.encrypt 行为一致。"""

    @staticmethod
    def encrypt(data: str, des_key: str) -> str:
        encrypted_hex = kingo_str_enc(data, des_key)
        return base64.b64encode(encrypted_hex.encode("utf-8")).decode("utf-8")


if __name__ == "__main__":
    # 自检：非空输出
    sample = KingoDES.encrypt("_u=abc&_p=def", "12345678ABCDEFGH")
    print("sample cipher:", sample)
    assert sample, "KingoDES encrypt should not return empty"
    print("KingoDES self-test passed")