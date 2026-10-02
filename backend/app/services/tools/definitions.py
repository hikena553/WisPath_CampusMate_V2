"""AI 工具定义（学生端 + 教师端）——纯数据列表，供 LLM function calling 使用。

p4_2 拆分自 tool_registry.py，与其他模块零依赖。
"""




TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_leave",
            "description": "创建请假申请。当学生表达请假意图时（如'请假'、'想请假'、'参加比赛需要请假'等），提取信息并自动创建请假申请",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "请假开始日期，格式YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "请假结束日期，格式YYYY-MM-DD"},
                    "reason": {"type": "string", "description": "请假原因"},
                    "leave_type": {"type": "string", "enum": ["competition", "sick", "personal", "other"], "description": "请假类型"}
                },
                "required": ["start_date", "end_date", "reason", "leave_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_growth_record",
            "description": "提取成长记录信息（不保存）。当学生提到获得了荣誉、竞赛获奖、取得奖项、参与实践、发表论文、取得成果，或上传了证明材料时，调用此工具提取信息，然后将提取结果展示给学生确认",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "记录标题"},
                    "record_type": {"type": "string", "enum": ["honor", "competition", "practice", "paper", "achievement"], "description": "类型：honor荣誉/competition竞赛/practice实践/paper论文/achievement成果"},
                    "description": {"type": "string", "description": "详细描述，从材料中提取关键信息，不要编造"},
                    "date": {"type": "string", "description": "发生日期，格式YYYY-MM-DD，从材料中提取，提取不到则留空"},
                    "honor_level": {"type": "string", "description": "荣誉等级：校级/省级/国家级/国际级"},
                    "organizer": {"type": "string", "description": "竞赛主办方"},
                    "competition_level": {"type": "string", "description": "竞赛等级：校级/省级/国家级/国际级"},
                    "practice_type": {"type": "string", "description": "实践类型：社会志愿活动/三下乡/支教/西部计划/筑梦扬帆计划/其他社会实践"},
                    "paper_type": {"type": "string", "description": "期刊类型：普刊/核心期刊/SCI/EI/顶刊/会议论文"},
                    "paper_name": {"type": "string", "description": "论文题目"},
                    "first_author": {"type": "string", "description": "第一作者"},
                    "achievement_type": {"type": "string", "description": "成果类型：发明专利/实用新型专利/软件著作权等"},
                    "achievement_name": {"type": "string", "description": "成果名称"},
                    "attachment_url": {"type": "string", "description": "证明材料URL，如果有上传文件则填写"}
                },
                "required": ["title", "record_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_growth_record",
            "description": "确认并保存成长记录。学生确认信息无误后调用此工具，将成长记录正式保存到数据库",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "记录标题"},
                    "record_type": {"type": "string", "enum": ["honor", "competition", "practice", "paper", "achievement"], "description": "类型"},
                    "description": {"type": "string", "description": "详细描述"},
                    "date": {"type": "string", "description": "发生日期，格式YYYY-MM-DD"},
                    "honor_level": {"type": "string", "description": "荣誉等级"},
                    "organizer": {"type": "string", "description": "竞赛主办方"},
                    "competition_level": {"type": "string", "description": "竞赛等级"},
                    "practice_type": {"type": "string", "description": "实践类型"},
                    "paper_type": {"type": "string", "description": "期刊类型"},
                    "paper_name": {"type": "string", "description": "论文题目"},
                    "first_author": {"type": "string", "description": "第一作者"},
                    "achievement_type": {"type": "string", "description": "成果类型"},
                    "achievement_name": {"type": "string", "description": "成果名称"},
                    "attachment_url": {"type": "string", "description": "证明材料URL"}
                },
                "required": ["title", "record_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_stage",
            "description": "更新项目对话的当前阶段进度。当项目对话中用户完成了当前阶段目标时，调用此工具推进到下一阶段",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "description": "新的阶段名称，如'方案设计'、'实施优化'"}
                },
                "required": ["stage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_service_request",
            "description": "提交办事服务申请（在校证明、调宿申请等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "申请标题"},
                    "content": {"type": "string", "description": "申请内容详情"},
                    "request_type": {"type": "string", "enum": ["certificate", "other"], "description": "申请类型"}
                },
                "required": ["title", "content", "request_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_schedule",
            "description": "查询学生的课程表信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "查询日期，格式YYYY-MM-DD，不传则查本周"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_grades",
            "description": "查询学生的成绩和GPA信息",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_exams",
            "description": "查询学生的考试安排",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询校园知识库（办事流程、规章制度、校园导航等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sceneries",
            "description": "查询校园风景信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "enum": ["anzhou", "youxian"], "description": "校区：anzhou安州/youxian游仙，不传则查全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_announcements",
            "description": "查询教务处官网最新通知公告（实时抓取）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_grades",
            "description": "查询学生成绩数据用于学情分析，包括各科成绩、GPA、学分等。调用后根据返回数据进行分析",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_schedule",
            "description": "查询学生课程表数据用于学习规划分析。调用后根据返回的课表数据给出建议",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_growth",
            "description": "查询学生成长档案数据用于综合能力评估。调用后根据返回的成长记录给出建议",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_lost_found",
            "description": "检索失物招领处是否已有某个物品的记录。当学生说'我丢了XX'、'有没有人捡到XX'、'帮我查下失物招领'时必须先调用此工具查询，再决定是否登记。keyword 请填物品通用名（如'保温杯'），不要带'我的''黑色'等修饰词",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "物品关键词，多个词用空格分隔，如'保温杯'或'钱包 校园卡'"},
                    "item_type": {"type": "string", "enum": ["lost", "found", "all"], "description": "检索范围：found=别人捡到待领的（找自己丢的东西优先用这个），lost=他人的寻物启事，all=全部。默认 all"},
                    "limit": {"type": "integer", "description": "返回条数，默认5"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_lost_found",
            "description": "在失物招领处发布寻物启事或招领信息。仅当 search_lost_found 确认没有匹配记录后调用，用于直接帮学生登记",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["lost", "found"], "description": "lost=学生丢了东西（发寻物启事），found=学生捡到东西（发招领信息）"},
                    "title": {"type": "string", "description": "物品名称，简短含关键特征，如'黑色保温杯'"},
                    "description": {"type": "string", "description": "物品特征（颜色/品牌/外观/内含物），取自用户描述或图片识别结果，不要编造"},
                    "location": {"type": "string", "description": "丢失或拾到的地点，如'博雅楼3楼自习室'，未知则留空"},
                    "contact": {"type": "string", "description": "联系方式，留空则默认使用当前用户的手机号/学号"},
                    "image_url": {"type": "string", "description": "物品图片URL，用户上传了图片时必须填写"}
                },
                "required": ["type", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_plan_overview",
            "description": "查询学生的学习计划概览：长期目标、进行中的计划与进度、今日待办任务、打卡连续天数。当学生问'我的学习计划''今日任务''计划进度''打卡多少天'时调用",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_plan_stages",
            "description": "查询学习计划的闯关关卡（阶段任务流）：各关卡状态、任务完成进度、AI 评分与评估意见。当学生问'计划的关卡''阶段任务''闯关进度''第几关'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "integer", "description": "学习计划ID，不传则查询所有进行中计划的关卡"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_plan_stage",
            "description": "提交学习计划某关卡的阶段成果，AI 将评估打分（0-100）、综合评估、指出不足并给出后续调整建议。当学生说'提交第X关成果''完成这关了''上传阶段成果'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage_id": {"type": "integer", "description": "关卡（阶段）ID"},
                    "result": {"type": "string", "description": "阶段成果说明：完成了哪些任务、产出了什么、数据与收获"}
                },
                "required": ["stage_id", "result"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_portfolio",
            "description": "查询学生的作品集：项目经历、证书荣誉、简历情况。当学生问'我的作品集''有哪些项目''证书情况''简历'时调用",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_community_posts",
            "description": "查询交流社区的帖子：支持按分类筛选、关键词搜索、按热度排序。当学生问'社区里有什么''大家都在聊什么''某某话题的帖子'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "搜索关键词，不传则查全部"},
                    "category": {"type": "string", "enum": ["技术", "提问", "分享", "求助"], "description": "帖子分类，不传则查全部"},
                    "sort": {"type": "string", "enum": ["latest", "hot"], "description": "排序：latest最新/hot最热，默认 latest"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_community_post",
            "description": "在交流社区发布帖子。当学生表达了分享/提问/求助的内容并希望发到社区时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "帖子标题"},
                    "content": {"type": "string", "description": "帖子正文内容"},
                    "category": {"type": "string", "enum": ["技术", "提问", "分享", "求助"], "description": "帖子分类，默认分享"}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_resources",
            "description": "查询资源中心：学习资源（知识库）、校园信息、行业资讯以及我的收藏。当学生问'有什么学习资源''帮我找资料''我的收藏''就业信息'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "搜索关键词，不传则查全部"},
                    "category": {"type": "string", "enum": ["all", "learning", "industry", "campus"], "description": "资源分类：all全部/learning学习资源/industry行业资讯/campus校园信息，默认 all"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_profile_overview",
            "description": "查询学生的个人成长画像：技能、兴趣、长期目标、成长记录数、近期打卡情况。当学生问'我的画像''我的技能兴趣''成长目标'时调用",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


# ============ Teacher Tools ============

TEACHER_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_pending_leaves",
            "description": "查询名下学生待审批的请假申请。教师说'查看待批请假'、'有哪些请假'时调用",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_students",
            "description": "查询教师名下的学生列表及基本信息（成绩、成长记录数、危机等级等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "搜索关键词（姓名/学号/学院），不传则查全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_crisis_alerts",
            "description": "查询名下学生的心理危机预警列表。教师说'查看预警'、'有危机预警吗'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "resolved": {"type": "boolean", "description": "是否只看已处理的，不传则看全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_leave",
            "description": "审批请假申请（通过或驳回）。教师说'批准请假'、'同意'、'驳回'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "integer", "description": "请假申请ID"},
                    "action": {"type": "string", "enum": ["approve", "reject"], "description": "approve通过/reject驳回"},
                    "reject_reason": {"type": "string", "description": "驳回原因（驳回时必填）"}
                },
                "required": ["leave_id", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_student_detail",
            "description": "查看某个学生的详细信息（成长记录、项目、危机预警、请假记录等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {"type": "string", "description": "学生姓名"}
                },
                "required": ["student_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_growth_stats",
            "description": "查看名下学生的成长统计数据（各类型记录数量）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询校园知识库（办事流程、规章制度、校园导航等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_announcements",
            "description": "查询教务处官网最新通知公告（实时抓取）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_leave",
            "description": "查询请假申请的详细信息用于审批分析，包括学生信息、请假原因、时间等。教师说'分析这个请假'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "integer", "description": "请假申请ID"}
                },
                "required": ["leave_id"]
            }
        }
    },
]
