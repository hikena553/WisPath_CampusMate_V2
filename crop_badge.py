from PIL import Image, ImageDraw
import os

def crop_to_circle(input_path, output_path, size=None):
    """将图片裁剪为圆形，保留透明背景"""
    img = Image.open(input_path).convert("RGBA")

    if size:
        img = img.resize((size, size), Image.LANCZOS)

    # 创建圆形蒙版
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)

    # 绘制圆形
    center = img.size[0] // 2
    radius = min(img.size) // 2
    draw.ellipse(
        [center - radius, center - radius, center + radius, center + radius],
        fill=255
    )

    # 应用蒙版
    output = Image.new("RGBA", img.size, (0, 0, 0, 0))
    output.paste(img, mask=mask)

    # 保存为PNG（支持透明度）
    output.save(output_path, "PNG")
    print(f"已保存圆形校徽到: {output_path}")
    return output_path

if __name__ == "__main__":
    # 处理校徽
    input_file = "frontend/public/images/校徽.png"
    output_file = "frontend/public/images/校徽_圆形.png"

    if os.path.exists(input_file):
        crop_to_circle(input_file, output_file)
    else:
        print(f"文件不存在: {input_file}")
