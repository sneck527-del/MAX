
import json
import shutil
import os
from datetime import datetime


class ProjectManager:
    """项目管理系统"""
    
    def __init__(self):
        self.base_path = os.getcwd()
        self.projects_path = os.path.join(self.base_path, "项目")
        self.templates_path = os.path.join(self.base_path, "模板")
        
        # 确保目录存在
        os.makedirs(self.projects_path, exist_ok=True)
        os.makedirs(self.templates_path, exist_ok=True)
        
        # 保存模板文件
        self.save_template_files()
    
    def save_template_files(self):
        """保存模板文件"""
        template_files = [
            "材料库.json",
            "施工库.json",
            "房间信息.json",
            "报价模板.json"
        ]
        
        for file in template_files:
            src = os.path.join(self.base_path, file)
            dst = os.path.join(self.templates_path, file)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
    
    def create_project(self, project_name):
        """创建新项目"""
        # 生成项目文件夹名称：项目名_YYYYMMDD
        date_str = datetime.now().strftime("%Y%m%d")
        project_folder = f"{project_name}_{date_str}"
        project_path = os.path.join(self.projects_path, project_folder)
        
        # 如果已存在，添加序号
        counter = 1
        while os.path.exists(project_path):
            project_folder = f"{project_name}_{date_str}_{counter}"
            project_path = os.path.join(self.projects_path, project_folder)
            counter += 1
        
        os.makedirs(project_path)
        
        # 创建子文件夹
        os.makedirs(os.path.join(project_path, "图纸"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "报价"), exist_ok=True)
        os.makedirs(os.path.join(project_path, "数据"), exist_ok=True)
        
        # 复制模板文件
        for file in ["材料库.json", "施工库.json"]:
            src = os.path.join(self.templates_path, file)
            dst = os.path.join(project_path, "数据", file)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        
        print(f"✅ 项目已创建: {project_folder}")
        return project_path, project_folder
    
    def list_projects(self):
        """列出所有项目"""
        if not os.path.exists(self.projects_path):
            print("没有找到项目")
            return []
        
        projects = []
        for item in sorted(os.listdir(self.projects_path), reverse=True):
            item_path = os.path.join(self.projects_path, item)
            if os.path.isdir(item_path):
                projects.append(item)
        
        print("\n" + "=" * 60)
        print("项目列表")
        print("=" * 60)
        for i, project in enumerate(projects, 1):
            print(f"{i:2d}. {project}")
        
        return projects
    
    def save_room_info(self, project_path, room_info):
        """保存房间信息到项目"""
        room_info_path = os.path.join(project_path, "数据", "房间信息.json")
        with open(room_info_path, 'w', encoding='utf-8') as f:
            json.dump(room_info, f, ensure_ascii=False, indent=2)
        print("✅ 房间信息已保存")
    
    def save_quote(self, project_path, quote_data, filename="报价单.json"):
        """保存报价到项目"""
        quote_path = os.path.join(project_path, "报价", filename)
        with open(quote_path, 'w', encoding='utf-8') as f:
            json.dump(quote_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 报价已保存: {filename}")
    
    def save_drawing(self, project_path, drawing_path):
        """保存图纸到项目"""
        if os.path.exists(drawing_path):
            filename = os.path.basename(drawing_path)
            dst = os.path.join(project_path, "图纸", filename)
            shutil.copy2(drawing_path, dst)
            print(f"✅ 图纸已保存: {filename}")
    
    def load_project(self, project_folder):
        """加载项目数据"""
        project_path = os.path.join(self.projects_path, project_folder)
        if not os.path.exists(project_path):
            print("❌ 项目不存在")
            return None
        
        print(f"\n📂 加载项目: {project_folder}")
        return project_path


class RenovationQuote:
    """装修报价生成器"""
    
    def __init__(self, project_path=None):
        self.project_path = project_path
        if project_path:
            self.data_path = os.path.join(project_path, "数据")
        else:
            self.data_path = os.getcwd()
        
        self.material_lib = None
        self.construction_lib = None
        self.room_info = None
        self.include_materials = True
        self.room_selections = {}
    
    def load_libraries(self):
        """加载报价库"""
        print("正在加载报价库...")
        try:
            with open(os.path.join(self.data_path, '材料库.json'), 'r', encoding='utf-8') as f:
                self.material_lib = json.load(f)
            with open(os.path.join(self.data_path, '施工库.json'), 'r', encoding='utf-8') as f:
                self.construction_lib = json.load(f)
            
            room_info_file = os.path.join(self.data_path, '房间信息.json')
            if os.path.exists(room_info_file):
                with open(room_info_file, 'r', encoding='utf-8') as f:
                    self.room_info = json.load(f)
            
            print("✅ 报价库加载成功！")
            return True
        except FileNotFoundError as e:
            print(f"❌ 找不到文件: {e}")
            return False
    
    def set_room_info(self, room_info):
        """设置房间信息"""
        self.room_info = room_info
    
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
        if not self.room_info:
            print("❌ 没有房间信息，请先设置房间信息")
            return False
        
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
            print(f"   面积: 地面={room['地面面积']}㎡, 墙面={room['墙面面积']}㎡, 顶面={room['顶面面积']}㎡")
            
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
        
        return True
    
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
        
        cat_choice = input(f"请选择分类 (1-{len(available_categories)}，或直接回车跳过): ").strip()
        
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
        print(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"主材: {'包含' if self.include_materials else '不包含主材'}")
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


def main():
    print("\n" + "=" * 60)
    print("🏠 装修报价管理系统")
    print("=" * 60)
    
    project_manager = ProjectManager()
    
    while True:
        print("\n" + "-" * 60)
        print("主菜单:")
        print("  1. 创建新项目")
        print("  2. 查看项目列表")
        print("  3. 打开现有项目")
        print("  4. 快速报价（使用当前目录）")
        print("  q. 退出")
        
        choice = input("\n请选择操作: ").strip().lower()
        
        if choice == '1':
            # 创建新项目
            project_name = input("\n请输入项目名称: ").strip()
            if project_name:
                project_path, project_folder = project_manager.create_project(project_name)
                
                # 复制当前房间信息（如果存在）
                current_room_info = os.path.join(os.getcwd(), "房间信息.json")
                if os.path.exists(current_room_info):
                    with open(current_room_info, 'r', encoding='utf-8') as f:
                        room_info = json.load(f)
                    project_manager.save_room_info(project_path, room_info)
                
                # 询问是否立即开始报价
                start_quote = input("\n是否立即开始报价？(y/n): ").strip().lower()
                if start_quote == 'y':
                    quote = RenovationQuote(project_path)
                    if quote.load_libraries():
                        quote.display_categories()
                        if quote.get_user_preferences():
                            quote_data = quote.generate_quote()
                            project_manager.save_quote(project_path, quote_data)
        
        elif choice == '2':
            # 查看项目列表
            project_manager.list_projects()
        
        elif choice == '3':
            # 打开现有项目
            projects = project_manager.list_projects()
            if projects:
                choice_idx = input("\n请选择项目编号: ").strip()
                if choice_idx.isdigit() and 1 <= int(choice_idx) <= len(projects):
                    project_folder = projects[int(choice_idx) - 1]
                    project_path = project_manager.load_project(project_folder)
                    
                    if project_path:
                        quote = RenovationQuote(project_path)
                        if quote.load_libraries():
                            quote.display_categories()
                            if quote.get_user_preferences():
                                quote_data = quote.generate_quote()
                                quote_filename = f"报价单_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                                project_manager.save_quote(project_path, quote_data, quote_filename)
        
        elif choice == '4':
            # 快速报价
            quote = RenovationQuote()
            if quote.load_libraries():
                quote.display_categories()
                if quote.get_user_preferences():
                    quote_data = quote.generate_quote()
                    
                    # 保存到当前目录
                    quote_filename = f"报价单_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(quote_filename, 'w', encoding='utf-8') as f:
                        json.dump(quote_data, f, ensure_ascii=False, indent=2)
                    print(f"报价已保存: {quote_filename}")
        
        elif choice == 'q':
            print("👋 再见！")
            break


if __name__ == "__main__":
    main()

