"""飞书多维表格结构定义：9张表的字段规格，供 max init 自动建表"""

# 飞书字段类型常量
TEXT = 1        # 多行文本
SINGLE_SELECT = 3  # 单选
DATE = 5        # 日期
NUMBER = 2      # 数字
LINK = 15       # 关联（关联网表）
LOOKUP = 17     # 引用（自动从关联表拉取）
AUTO_NUMBER = 9 # 自动编号

BITABLE_TABLES = [
    {
        "name": "客户信息",
        "description": "客户基本信息与跟进状态",
        "env_key": "BITABLE_TABLE_CLIENTS",
        "fields": [
            {"field_name": "客户编号", "type": AUTO_NUMBER},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "性别", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "男"}, {"name": "女"},
            ]}},
            {"field_name": "联系方式", "type": TEXT},
            {"field_name": "客户类型", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "新客户"}, {"name": "老客户"}, {"name": "意向客户"}, {"name": "成交客户"},
            ]}},
            {"field_name": "客户来源", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "小红书"}, {"name": "抖音"}, {"name": "转介绍"}, {"name": "线下"}, {"name": "其他"},
            ]}},
            {"field_name": "项目地址", "type": TEXT},
            {"field_name": "类型", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "住宅"}, {"name": "商业"}, {"name": "办公"},
            ]}},
            {"field_name": "户型", "type": TEXT},
            {"field_name": "面积", "type": NUMBER},
            {"field_name": "报价", "type": NUMBER},
            {"field_name": "设计费", "type": NUMBER},
            {"field_name": "录入人", "type": TEXT},
            {"field_name": "部门", "type": TEXT},
            {"field_name": "分派设计师", "type": TEXT},
            {"field_name": "录入时间", "type": DATE},
            {"field_name": "跟进时间", "type": DATE},
            {"field_name": "落单进度", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "初访"}, {"name": "量房"}, {"name": "方案"}, {"name": "报价"}, {"name": "签约"},
            ]}},
            {"field_name": "服务阶段", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "洽谈"}, {"name": "设计"}, {"name": "施工"}, {"name": "竣工"}, {"name": "售后"},
            ]}},
            {"field_name": "备注", "type": TEXT},
        ],
    },
    {
        "name": "合同管理",
        "description": "合同与付款信息",
        "env_key": "BITABLE_TABLE_CONTRACTS",
        "fields": [
            {"field_name": "合同编号", "type": AUTO_NUMBER},
            {"field_name": "签订日期", "type": DATE},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "项目地址", "type": TEXT},
            {"field_name": "轻辅合同", "type": NUMBER},
            {"field_name": "主材合同额", "type": NUMBER},
            {"field_name": "直接费", "type": NUMBER},
            {"field_name": "产值", "type": NUMBER},
            {"field_name": "预估利润", "type": NUMBER},
            {"field_name": "盈余", "type": NUMBER},
            {"field_name": "支出", "type": NUMBER},
            {"field_name": "设计费", "type": NUMBER},
            {"field_name": "付款比例", "type": TEXT},
            {"field_name": "已付款", "type": NUMBER},
            {"field_name": "剩余款", "type": NUMBER},
            {"field_name": "首期款", "type": NUMBER},
            {"field_name": "中期款", "type": NUMBER},
            {"field_name": "尾期款", "type": NUMBER},
            {"field_name": "主材款", "type": NUMBER},
            {"field_name": "增减项", "type": NUMBER},
            {"field_name": "设计师", "type": TEXT},
            {"field_name": "备注", "type": TEXT},
        ],
    },
    {
        "name": "合作商",
        "description": "供应商与合作方信息",
        "env_key": "BITABLE_TABLE_SUPPLIERS",
        "fields": [
            {"field_name": "姓名", "type": TEXT},
            {"field_name": "联系电话", "type": TEXT},
            {"field_name": "邮箱地址", "type": TEXT},
            {"field_name": "合作类型", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "材料商"}, {"name": "施工队"}, {"name": "设计师"}, {"name": "其他"},
            ]}},
            {"field_name": "品牌/工种", "type": TEXT},
            {"field_name": "供应产品", "type": TEXT},
            {"field_name": "报价清单", "type": TEXT},
            {"field_name": "合作评分", "type": NUMBER},
            {"field_name": "合作等级", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "A级"}, {"name": "B级"}, {"name": "C级"},
            ]}},
        ],
    },
    {
        "name": "支出明细",
        "description": "项目支出记录",
        "env_key": "BITABLE_TABLE_EXPENSE",
        "fields": [
            {"field_name": "日期", "type": DATE},
            {"field_name": "合同编号", "type": TEXT},
            {"field_name": "项目地址", "type": TEXT},
            {"field_name": "支出明细", "type": TEXT},
            {"field_name": "往来单位", "type": TEXT},
            {"field_name": "联系方式", "type": TEXT},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "支出", "type": NUMBER},
            {"field_name": "备注", "type": TEXT},
            {"field_name": "附件", "type": TEXT},
        ],
    },
    {
        "name": "收入明细",
        "description": "项目收入记录",
        "env_key": "BITABLE_TABLE_INCOME",
        "fields": [
            {"field_name": "编号", "type": AUTO_NUMBER},
            {"field_name": "合同编号", "type": TEXT},
            {"field_name": "项目地址", "type": TEXT},
            {"field_name": "首期款", "type": NUMBER},
            {"field_name": "中期款", "type": NUMBER},
            {"field_name": "尾期款", "type": NUMBER},
            {"field_name": "主材款", "type": NUMBER},
            {"field_name": "设计费", "type": NUMBER},
            {"field_name": "增减项", "type": NUMBER},
            {"field_name": "收入总和", "type": NUMBER},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "联系方式", "type": TEXT},
            {"field_name": "备注", "type": TEXT},
            {"field_name": "附件", "type": TEXT},
        ],
    },
    {
        "name": "施工管理",
        "description": "施工进度与任务管理",
        "env_key": "BITABLE_TABLE_CONSTRUCTION",
        "fields": [
            {"field_name": "施工节点", "type": TEXT},
            {"field_name": "节点说明", "type": TEXT},
            {"field_name": "执行人", "type": TEXT},
            {"field_name": "完结", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "未开始"}, {"name": "进行中"}, {"name": "已完成"},
            ]}},
            {"field_name": "任务", "type": TEXT},
            {"field_name": "子任务", "type": TEXT},
            {"field_name": "计划日期", "type": DATE},
            {"field_name": "实际日期", "type": DATE},
        ],
    },
    {
        "name": "任务",
        "description": "工种任务清单",
        "env_key": "BITABLE_TABLE_TASKS",
        "fields": [
            {"field_name": "施工节点", "type": TEXT},
            {"field_name": "分类", "type": TEXT},
            {"field_name": "工种", "type": TEXT},
            {"field_name": "预埋", "type": TEXT},
            {"field_name": "采购", "type": TEXT},
            {"field_name": "污染", "type": TEXT},
            {"field_name": "进度", "type": TEXT},
        ],
    },
    {
        "name": "售后维保台账",
        "description": "售后问题处理与维保记录",
        "env_key": "BITABLE_TABLE_AFTER_SALES",
        "fields": [
            {"field_name": "提报日期", "type": DATE},
            {"field_name": "合同编号", "type": TEXT},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "问题类型", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "水电"}, {"name": "墙面"}, {"name": "防水"},
                {"name": "门窗"}, {"name": "柜体"}, {"name": "其他"},
            ]}},
            {"field_name": "问题描述", "type": TEXT},
            {"field_name": "处理状态", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "待处理"}, {"name": "处理中"}, {"name": "已完成"}, {"name": "已关闭"},
            ]}},
            {"field_name": "优先级", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "紧急"}, {"name": "高"}, {"name": "中"}, {"name": "低"},
            ]}},
            {"field_name": "提报人", "type": TEXT},
            {"field_name": "处理人", "type": TEXT},
            {"field_name": "处理完成日期", "type": DATE},
            {"field_name": "客户满意度", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "非常满意"}, {"name": "满意"}, {"name": "一般"}, {"name": "不满意"},
            ]}},
            {"field_name": "备注", "type": TEXT},
        ],
    },
    {
        "name": "跟进记录表",
        "description": "客户跟进与回访记录",
        "env_key": "BITABLE_TABLE_FOLLOWUPS",
        "fields": [
            {"field_name": "跟进时间", "type": DATE},
            {"field_name": "合同编号", "type": TEXT},
            {"field_name": "客户姓名", "type": TEXT},
            {"field_name": "记录类型", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "日常跟进"}, {"name": "售后回访"}, {"name": "关怀回访"}, {"name": "投诉跟进"},
            ]}},
            {"field_name": "跟进人", "type": TEXT},
            {"field_name": "跟进方式", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "微信"}, {"name": "电话"}, {"name": "面访"}, {"name": "飞书"},
            ]}},
            {"field_name": "跟进内容", "type": TEXT},
            {"field_name": "客户反馈", "type": TEXT},
            {"field_name": "满意度", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "非常满意"}, {"name": "满意"}, {"name": "一般"}, {"name": "不满意"},
            ]}},
            {"field_name": "跟进事项", "type": TEXT},
            {"field_name": "下次跟进时间", "type": DATE},
            {"field_name": "状态", "type": SINGLE_SELECT, "property": {"options": [
                {"name": "待跟进"}, {"name": "跟进中"}, {"name": "已完成"},
            ]}},
        ],
    },
]
