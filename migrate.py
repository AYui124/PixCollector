#!/usr/bin/env python3
"""数据库迁移脚本."""
from typing import TypedDict

from app import create_app
from database import create_tables
from models import SchedulerConfig, SystemConfig, User, db


class ConfigValue(TypedDict):
    value: str | None
    type: str
    desc: str


app = create_app()


# def migrate_add_last_run_time_column():
#     """添加last_run_time字段到scheduler_configs表."""
#     # 检查last_run_time字段是否已存在（使用DESCRIBE命令）
#     result = db.session.execute(text("DESCRIBE scheduler_configs"))
#     columns = result.fetchall()
#     column_names = [col[0] for col in columns]

#     if 'last_run_time' in column_names:
#         print(
#             "  Skipped: last_run_time column already "
#             "exists in scheduler_configs table"
#         )
#         return

#     # 添加last_run_time字段
#     print("  Adding last_run_time column to scheduler_configs table...")
#     db.session.execute(text(
#         "ALTER TABLE scheduler_configs ADD COLUMN "
#         "last_run_time DATETIME NULL COMMENT '任务最后执行时间'"
#     ))

#     db.session.commit()
#     print("  Added: last_run_time column to scheduler_configs table")


# def migrate_add_post_date_column():
#     """添加post_date字段到artworks表."""
#     # 检查post_date字段是否已存在（使用DESCRIBE命令）
#     result = db.session.execute(text("DESCRIBE artworks"))
#     columns = result.fetchall()
#     column_names = [col[0] for col in columns]

#     if 'post_date' in column_names:
#         print("  Skipped: post_date column already exists in artworks table")
#         return
#     print("  Adding post_date column to artworks table...")
#     db.session.execute(text(
#         "ALTER TABLE artworks ADD COLUMN post_date DATETIME "
#         "NOT NULL COMMENT '作品创作时间'"
#     ))

#     # 添加索引
#     db.session.execute(text(
#         "CREATE INDEX idx_post_date ON artworks(post_date)"
#     ))

#     db.session.commit()
#     print("  Added: post_date column to artworks table")


# def migrate_add_type_column():
#     """添加type字段到artworks表."""

#     # 检查type字段是否已存在（使用DESCRIBE命令）
#     result = db.session.execute(text("DESCRIBE artworks"))
#     columns = result.fetchall()
#     column_names = [col[0] for col in columns]

#     if 'type' in column_names:
#         print("  Skipped: type column already exists in artworks table")
#         return

#     # 添加type字段
#     print("  Adding type column to artworks table...")
#     db.session.execute(text(
#         "ALTER TABLE artworks ADD COLUMN type VARCHAR(20) "
#         "NOT NULL DEFAULT 'illust' COMMENT '作品类型: illust, manga, ugoira'"
#     ))

#     # 添加索引
#     db.session.execute(text(
#         "CREATE INDEX ix_artworks_type ON artworks(type)"
#     ))

#     db.session.commit()
#     print("  Added: type column to artworks table")


def insert_defualt_scheduler_config():
    """插入默认SchedulerConfig"""
    config_mapping: dict[str, str] = {
        'ranking_works': '0 13 * * *',
        'follow_new_follow': '0 */6 * * *',
        'follow_new_works': '0 */1 * * *',
        'update_artworks': '0 */4 * * *',
        'clean_up_logs': '0 0 4 * * *'
    }
    migrated_count = 0
    for key, expression in config_mapping.items():
        existing = db.session.query(SchedulerConfig).filter_by(
            collect_type=key
        ).first()
        if not existing:
            config_item = SchedulerConfig(
                collect_type=key,
                crontab_expression=expression,
                is_active=False
            )
            db.session.add(config_item)
            migrated_count += 1
            print(f"  Created: {key}")
        else:
            print(f"  Skipped: {key} (already exists)")

    db.session.commit()
    print(f"Migration completed: {migrated_count} config created.")


def insert_default_system_config():
    """插入默认SystemrConfig"""
    # 定义配置项映射
    config_mapping: dict[str, ConfigValue] = {
        # Pixiv认证配置
        'refresh_token': {
            'value': None,
            'type': 'string',
            'desc': 'Pixiv Refresh Token'
        },
        'access_token': {
            'value': None,
            'type': 'string',
            'desc': 'Pixiv Access Token'
        },
        'token_expires_at': {
            'value': None,
            'type': 'datetime',
            'desc': 'Token过期时间'
        },

        # 采集配置
        'update_interval_days': {
            'value': '7',
            'type': 'integer',
            'desc': '作品更新间隔天数'
        },
        'update_max_per_run': {
            'value': '200',
            'type': 'integer',
            'desc': '批量更新作品数量'
        },
        'invalid_artwork_action': {
            'value': 'Mark',
            'type': 'string',
            'desc': '失效作品处理方式'
        },
        'new_user_backtrack_years': {
            'value': '2',
            'type': 'integer',
            'desc': '新用户回采年数'
        },
        'log_retention_days': {
            'value': '30',
            'type': 'integer',
            'desc': '采集日志保留天数'
        },

        # 速率限制配置
        'api_delay_min': {
            'value': '1',
            'type': 'float',
            'desc': 'API请求最小延迟（秒）'
        },
        'api_delay_max': {
            'value': '3',
            'type': 'float',
            'desc': 'API请求最大延迟（秒）'
        },
        'error_delay_429_min': {
            'value': '30',
            'type': 'float',
            'desc': '429错误最小延迟（秒）'
        },
        'error_delay_429_max': {
            'value': '60',
            'type': 'float',
            'desc': '429错误最大延迟（秒）'
        },
        'error_delay_403_min': {
            'value': '30',
            'type': 'float',
            'desc': '403错误最小延迟（秒）'
        },
        'error_delay_403_max': {
            'value': '50',
            'type': 'float',
            'desc': '403错误最大延迟（秒）'
        },
        'error_delay_other_min': {
            'value': '10',
            'type': 'float',
            'desc': '其他错误最小延迟（秒）'
        },
        'error_delay_other_max': {
            'value': '30',
            'type': 'float',
            'desc': '其他错误最大延迟（秒）'
        }
    }

    # 创建或更新配置项
    migrated_count = 0
    for key, item_info in config_mapping.items():
        existing = db.session.query(SystemConfig).filter_by(
            config_key=key
        ).first()
        if not existing:
            config_item = SystemConfig(
                config_key=key,
                config_value=item_info['value'],
                value_type=item_info['type'],
                description=item_info['desc']
            )
            db.session.add(config_item)
            migrated_count += 1
            print(f"  Created: {key}")
        else:
            print(f"  Skipped: {key} (already exists)")

    db.session.commit()
    print(f"Migration completed: {migrated_count} config created.")


if __name__ == '__main__':
    with app.app_context():
        print("Creating database tables...")
        create_tables(app)

        # SchedulerConfig默认值
        insert_defualt_scheduler_config()

        # SystemConfig默认值
        insert_default_system_config()

        # 检查用户
        if db.session.query(User).count() == 0:
            print("\nNo users found.")
            print("Please initialize system via API:")
            print(' Set user and password in .env')
            print("  POST /api/init")
        else:
            print("\nFound user(s).")

        print("\nDatabase migration completed successfully!")
