
import json
from datetime import datetime


class RenovationQuote:
    def __init__(self):
        self.material_lib = None  # 主材库
        self.construction_lib = None  # 施工库（轻工辅料）
        self.room_info = None  # 房间信息
        self.include_materials = True  # 是否包含主材
        self.room_selections = {}  # 每个房间的选择

    def load_libraries(self):
        """加载报价库"""
        print("正在加载报价库...")
        try:
            with open('材料库.json', 'r', encoding='utf-8') as f:
                self.material_lib = json.load(f)
            with open('施工库.json', 'r', encoding='utf-8') as f:
                self.construction_lib = json.load(f)
            with open('房间信息.json', 'r', encoding='utf-8') as f:
                self.room_info = json.load(f)
            print("报价库加载成功！")
            return True
        except FileNotFoundError as e:
            print(f"找不到文件: {e}")
            return False

    def display_categories(self):
        """显示报价库分类"""
        print("\n" + "=" * 60)
        print("主材库分类:")
        for category in sorted(self.material_lib.keys()):
            subcats = list(self.material_lib[category].keys())
            print(f"  - {category} ({len(subcats)} 个子分类)")
        
        print("\n施工库分类:")
        for category in sorted(self.construction_lib.keys()):
            items = len(self.construction_lib[category])
            print(f"  - {category} ({items} 个项目)")
        print("=" * 60)

    def get_user_preferences(self):
        """获取用户偏好"""
        print("\n" + "=" * 60)
        print("装修报价配置")
        print("=" * 60)
        
        # 询问是否包含主材
        include_input = input("\n是否包含主材？(y/n，默认y): ").strip().lower()
        self.include_materials = include_input != 'n'
        print(f"{'包含主材' if self.include_materials else '不包含主材'}")
        
        # 为每个房间选择材料和施工项目
        print("\n请为每个房间配置装修:")
        for room in self.room_info['房间']:
            print(f"\n--- {room['名称']} ---")
            print(f"  面积: 地面={room['地面面积']}㎡, 墙面={room['墙面面积']}㎡, 顶面={room['顶面面积']}㎡")
            
            self.room_selections[room['名称']] = {
                'room': room,
                'floor_material': None,
                'wall_material': None,
                'ceiling_material': None,
                'construction_items': []
            }
            
            # 选择地面主材
            if self.include_materials:
                self.room_selections[room['名称']]['floor_material'] = \
                    self.select_material('地面', '请选择地面材料')
            
            # 选择墙面主材
            if self.include_materials:
                self.room_selections[room['名称']]['wall_material'] = \
                    self.select_material('墙面', '请选择墙面材料')
            
            # 选择顶面主材
            if self.include_materials:
                self.room_selections[room['名称']]['ceiling_material'] = \
                    self.select_material('顶面', '请选择顶面材料')
            
            # 选择施工项目
            self.room_selections[room['名称']]['construction_items'] = \
                self.select_construction_items(room['名称'])

    def select_material(self, category_name, prompt):
        """选择主材"""
        print(f"\n{prompt}:")
        
        # 查找相关分类
        available_categories = []
        for cat in self.material_lib.keys():
            if category_name in cat or any(category_name in sub for sub in self.material_lib[cat]):
                available_categories.append(cat)
        
        if not available_categories:
            available_categories = list(self.material_lib.keys())
        
        print("可用分类:")
        for i, cat in enumerate(available_categories, 1):
            print(f"  {i}. {cat}")
        
        cat_choice = input(f"请选择分类 (1-{len(available_categories)}, 或直接回车跳过): ").strip()
        
        if not cat_choice:
            return None
        
        try:
            selected_cat = available_categories[int(cat_choice) - 1]
            
            # 显示该分类下的子分类
            subcats = list(self.material_lib[selected_cat].keys())
            print(f"\n{subcats}子分类:")
            for i, subcat in enumerate(subcats, 1):
                print(f"  {i}. {subcat}")
            
            subcat_choice = input(f"请选择子分类 (1-{len(subcats)}): ").strip()
            if subcat_choice and subcat_choice.isdigit():
                selected_subcat = subcats[int(subcat_choice) - 1]
                
                # 显示具体材料
                items = self.material_lib[selected_cat][selected_subcat]
                print(f"\n可用材料:")
                for i, item in enumerate(items, 1):
                    print(f"  {i}. {item['名称']} - {item['单价']}{item['单位']}")
                
                item_choice = input(f"请选择材料 (1-{len(items)}): ").strip()
                if item_choice and item_choice.isdigit():
                    selected_item = items[int(item_choice) - 1]
                    print(f"已选择: {selected_item['名称']}")
                    return {
                        'category': selected_cat,
                        'subcategory': selected_subcat,
                        'item': selected_item
                    }
        except (ValueError, IndexError):
            print("输入无效，跳过")
        
        return None

    def select_construction_items(self, room_name):
        """选择施工项目"""
        print(f"\n请为{room_name}选择施工项目:")
        
        selected_items = []
        
        # 列出常用施工分类
        common_categories = ['地面', '墙面', '顶面', '水电', '防水']
        
        for cat in common_categories:
            # 查找匹配的分类
            matching_cats = [c for c in self.construction_lib.keys() if cat in c]
            
            if matching_cats:
                print(f"\n--- {matching_cats[0]} ---")
                items = self.construction_lib[matching_cats[0]]
                
                for i, item in enumerate(items, 1):
                    print(f"  {i}. {item['项目']} - {item['综合报价']}{item['单位']}")
                
                choice = input(f"请选择要添加的项目编号(多个用逗号分隔，回车跳过): ").strip()
                
                if choice:
                    for c in choice.split(','):
                        try:
                            idx = int(c.strip()) - 1
                            if 0 <= idx < len(items):
                                selected_items.append({
                                    'category': matching_cats[0],
                                    'item': items[idx]
                                })
                                print(f"已添加: {items[idx]['项目']}")
                        except (ValueError, IndexError):
                            pass
        
        return selected_items

    def calculate_room_cost(self, room_name):
        """计算单个房间的费用"""
        selection = self.room_selections[room_name]
        room = selection['room']
        
        total_material = 0.0
        total_construction = 0.0
        details = []
        
        # 计算主材费用
        if self.include_materials:
            # 地面
            if selection['floor_material']:
                item = selection['floor_material']['item']
                area = room['地面面积']
                # 注意：需要根据单位转换，这里简化处理
                cost = item['单价'] * area
                total_material += cost
                details.append({
                    'type': '主材',
                    'name': item['名称'],
                    'area': area,
                    'unit': item['单位'],
                    'cost': cost
                })
            
            # 墙面
            if selection['wall_material']:
                item = selection['wall_material']['item']
                area = room['墙面面积']
                cost = item['单价'] * area
                total_material += cost
                details.append({
                    'type': '主材',
                    'name': item['名称'],
                    'area': area,
                    'unit': item['单位'],
                    'cost': cost
                })
            
            # 顶面
            if selection['ceiling_material']:
                item = selection['ceiling_material']['item']
                area = room['顶面面积']
                cost = item['单价'] * area
                total_material += cost
                details.append({
                    'type': '主材',
                    'name': item['名称'],
                    'area': area,
                    'unit': item['单位'],
                    'cost': cost
                })
        
        # 计算施工费用
        for construction in selection['construction_items']:
            item = construction['item']
            
            # 确定数量
            qty = 1.0
            if item['单位'] == '平米':
                if '地面' in construction['category']:
                    qty = room['地面面积']
                elif '墙面' in construction['category']:
                    qty = room['墙面面积']
                elif '顶面' in construction['category']:
                    qty = room['顶面面积']
                else:
                    qty = room['地面面积']
            
            cost = item['综合报价'] * qty
            total_construction += cost
            details.append({
                'type': '施工',
                'name': item['项目'],
                'qty': qty,
                'unit': item['单位'],
                'cost': cost
            })
        
        return {
            'details': details,
            'total_material': total_material,
            'total_construction': total_construction,
            'total': total_material + total_construction
        }

    def generate_quote(self):
        """生成报价"""
        print("\n" + "=" * 60)
        print("全屋装修报价单")
        print("=" * 60)
        print(f"生成日期: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"主材: {'包含' if self.include_materials else '不包含'}")
        print("=" * 60)
        
        grand_total_material = 0.0
        grand_total_construction = 0.0
        all_room_costs = {}
        
        # 计算每个房间
        for room_name in self.room_selections:
            room_cost = self.calculate_room_cost(room_name)
            all_room_costs[room_name] = room_cost
            
            grand_total_material += room_cost['total_material']
            grand_total_construction += room_cost['total_construction']
            
            print(f"\n【{room_name}】")
            for detail in room_cost['details']:
                if detail['type'] == '主材':
                    print(f"  {detail['name']}: {detail['cost']:.2f}元 ({detail['area']}{detail['unit']})")
                else:
                    print(f"  {detail['name']}: {detail['cost']:.2f}元 ({detail['qty']}{detail['unit']})")
            print(f"  小计: {room_cost['total']:.2f}元")
        
        grand_total = grand_total_material + grand_total_construction
        
        print("\n" + "=" * 60)
        print("【报价汇总】")
        if self.include_materials:
            print(f"主材费用总计: {grand_total_material:.2f}元")
        print(f"施工费用总计: {grand_total_construction:.2f}元")
        print(f"工程总报价: {grand_total:.2f}元")
        print("=" * 60)
        
        return {
            'room_costs': all_room_costs,
            'total_material': grand_total_material,
            'total_construction': grand_total_construction,
            'grand_total': grand_total
        }

    def save_quote(self, quote_data, filename="报价单.json"):
        """保存报价单"""
        output = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'include_materials': self.include_materials,
            'room_selections': self.room_selections,
            'quote_data': quote_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n报价单已保存到: {filename}")


def main():
    quote = RenovationQuote()
    
    # 加载报价库
    if not quote.load_libraries():
        print("无法继续，请确保所有报价库文件存在")
        return
    
    # 显示分类
    quote.display_categories()
    
    # 获取用户偏好
    quote.get_user_preferences()
    
    # 生成报价
    quote_data = quote.generate_quote()
    
    # 保存报价
    quote.save_quote(quote_data)


if __name__ == "__main__":
    main()

