"""测试 VLM 视觉分析服务"""
from PIL import Image, ImageDraw, ImageFont
import os
from app.services.vision_service import vision_service


def create_test_image(filename: str) -> str:
    """创建一个测试用的简单图片"""
    # 创建 400x400 的图片
    img = Image.new('RGB', (400, 400), color='#8B4513')
    draw = ImageDraw.Draw(img)
    
    # 画一个简单的"旧书"形状
    draw.rectangle([100, 100, 300, 300], fill='#A0522D', outline='#5D4037', width=3)
    draw.line([120, 120, 280, 120], fill='#5D4037', width=2)
    draw.line([120, 140, 280, 140], fill='#5D4037', width=2)
    draw.line([120, 160, 280, 160], fill='#5D4037', width=2)
    
    # 添加文字
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    draw.text((140, 200), "OLD BOOK", fill='#3E2723', font=font)
    
    filepath = f"./uploads/{filename}"
    img.save(filepath)
    print(f"测试图片已创建: {filepath}")
    return filepath


def test_vision_service():
    """测试视觉分析服务"""
    print("=" * 50)
    print("测试 VLM 视觉分析服务")
    print("=" * 50)
    
    # 创建测试图片
    test_image = create_test_image("test_book.jpg")
    
    print("\n正在调用 VLM 分析图片...")
    print("(如果 API Key 未配置，将使用 fallback 模式)\n")
    
    try:
        result = vision_service.analyze_with_fallback(test_image)
        
        print("✅ 分析成功!")
        print(f"\n物品名称: {result.item_name}")
        print(f"视觉特征: {', '.join(result.visual_features)}")
        print(f"性格特征: {', '.join(result.personality_traits)}")
        print(f"角色暗示: {result.story_character_hint}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")


if __name__ == "__main__":
    test_vision_service()
