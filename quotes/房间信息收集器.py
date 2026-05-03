
import json


# 从报价库中提取的标准房间类型
ROOM_TYPES = [
    "客厅", "厨房", "餐厅", "餐厨", "客卫", "主卫", 
    "书房", "客卧", "主卧", "儿童房（男）", "儿童房（女）",
    "衣帽间", "老人房", "保姆房", "阳台", "储物间",
    "影视厅", "茶室", "健身房", "换鞋间", "设备间",
    "洗衣房", "楼梯间", "全屋"
]


def collect_room_info():
    """收集房间信息的交互式工具"""
    print("=" * 60)
    print("房间信息收集器")
    print("=" * 60)
    print("\n可用的房间类型:")
    
    # 显示房间类型
    for i, room_type in enumerate(ROOM_TYPES, 1):
        if i % 6 == 1:
            print()
        print(f"  {i:2d}. {room_type}", end="")
    
    print("\n")
    rooms = []
    
    while True:
        print("\n" + "-" * 60)
        print("添加新房间（输入 'q' 完成）")
        
        choice = input("\n请选择房间类型编号或输入房间名: ").strip()
        
        if choice.lower() == 'q':
            break
        
        # 确定房间名称
        if choice.isdigit() and 1 <= int(choice) <= len(ROOM_TYPES):
            room_name = ROOM_TYPES[int(choice) - 1]
        else:
            room_name = choice
        
        try:
            floor_area = float(input(f"{room_name} - 地面面积 (㎡): ").strip())
            wall_area = float(input(f"{room_name} - 墙面面积 (㎡): ").strip())
            ceiling_area = float(input(f"{room_name} - 顶面面积 (㎡): ").strip())
            
            room = {
                "名称": room_name,
                "地面面积": floor_area,
                "墙面面积": wall_area,
                "顶面面积": ceiling_area
            }
            rooms.append(room)
            print(f"✅ 已添加: {room_name}")
            
        except ValueError:
            print("❌ 请输入有效的数字！")
            continue
    
    if rooms:
        print("\n" + "=" * 60)
        print("收集到的房间信息:")
        print("=" * 60)
        
        total_floor = 0.0
        total_wall = 0.0
        total_ceiling = 0.0
        
        for i, room in enumerate(rooms, 1):
            print(f"\n{i}. {room['名称']}")
            print(f"   地面: {room['地面面积']}㎡")
            print(f"   墙面: {room['墙面面积']}㎡")
            print(f"   顶面: {room['顶面面积']}㎡")
            
            total_floor += room['地面面积']
            total_wall += room['墙面面积']
            total_ceiling += room['顶面面积']
        
        print(f"\n📊 总计:")
        print(f"   房间数: {len(rooms)}")
        print(f"   地面总面积: {total_floor}㎡")
        print(f"   墙面总面积: {total_wall}㎡")
        print(f"   顶面总面积: {total_ceiling}㎡")
        
        save = input("\n💾 是否保存到房间信息.json？(y/n): ").strip().lower()
        if save == 'y':
            output = {"房间": rooms}
            with open('房间信息.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print("✅ 房间信息已保存！")
    else:
        print("没有收集到房间信息")


def load_and_display():
    """显示当前的房间信息"""
    try:
        with open('房间信息.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n" + "=" * 60)
        print("当前房间信息")
        print("=" * 60)
        
        total_floor = 0.0
        total_wall = 0.0
        total_ceiling = 0.0
        
        for i, room in enumerate(data['房间'], 1):
            print(f"\n{i}. {room['名称']}")
            print(f"   地面: {room['地面面积']}㎡")
            print(f"   墙面: {room['墙面面积']}㎡")
            print(f"   顶面: {room['顶面面积']}㎡")
            
            total_floor += room['地面面积']
            total_wall += room['墙面面积']
            total_ceiling += room['顶面面积']
        
        print(f"\n📊 总计:")
        print(f"   房间数: {len(data['房间'])}")
        print(f"   地面总面积: {total_floor}㎡")
        print(f"   墙面总面积: {total_wall}㎡")
        print(f"   顶面总面积: {total_ceiling}㎡")
        
        return data
    except FileNotFoundError:
        print("房间信息.json 不存在")
        return None


def main():
    print("\n" + "=" * 60)
    print("装修报价系统 - 房间信息管理")
    print("=" * 60)
    print("\n1. 收集新的房间信息")
    print("2. 查看当前房间信息")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == '1':
        collect_room_info()
    elif choice == '2':
        load_and_display()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

