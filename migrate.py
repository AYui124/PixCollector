#!/usr/bin/env python3
"""数据库迁移脚本."""
from typing import TypedDict

from sqlalchemy import select

from core.database import create_all_tables, session_scope
from models import SchedulerConfig, SystemConfig, User


class ConfigValue(TypedDict):
    value: str | None
    type: str
    desc: str


def insert_default_scheduler_config():
    """插入默认SchedulerConfig"""
    config_mapping: dict[str, str] = {
        'ranking_works': '0 13 * * *',
        'follow_new_follow': '0 */6 * * *',
        'follow_new_works': '0 */1 * * *',
        'update_artworks': '0 */4 * * *',
        'clean_up_logs': '0 4 * * *'
    }

    migrated_count = 0
    with session_scope() as session:
        for key, expression in config_mapping.items():
            existing = session.execute(
                select(SchedulerConfig).where(
                    SchedulerConfig.collect_type == key
                )
            ).scalar_one_or_none()

            if not existing:
                config_item = SchedulerConfig(
                    collect_type=key,
                    crontab_expression=expression,
                    is_active=False
                )
                session.add(config_item)
                migrated_count += 1
                print(f'  Created: {key}')
            else:
                print(f'  Skipped: {key} (already exists)')

    print(f'Migration completed: {migrated_count} config created.')


def insert_default_system_config():
    """插入默认SystemConfig"""
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
        'ranking_collect_pages': {
            'value': '5',
            'type': 'integer',
            'desc': '排行榜采集页数'
        },
        'custom_ranking_keywords': {
            'value': '',
            'type': 'string',
            'desc': '自定义榜单关键词列表'
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
    with session_scope() as session:
        for key, item_info in config_mapping.items():
            existing = session.execute(
                select(SystemConfig).where(
                    SystemConfig.config_key == key
                )
            ).scalar_one_or_none()

            if not existing:
                config_item = SystemConfig(
                    config_key=key,
                    config_value=item_info['value'],
                    value_type=item_info['type'],
                    description=item_info['desc']
                )
                session.add(config_item)
                migrated_count += 1
                print(f'  Created: {key}')
            else:
                print(f'  Skipped: {key} (already exists)')

    print(f'Migration completed: {migrated_count} config created.')


def check_user():
    """检查用户"""
    with session_scope() as session:
        result = session.execute(
            select(User.id)
        ).scalars().all()

        if not result:
            print('\nNo users found.')
            print('Please initialize system via API:')
            print(' Set user and password in .env')
            print('  POST /api/init')
        else:
            print(f'\nFound {len(result)} user(s).')


if __name__ == '__main__':
    print('Creating database tables...')
    create_all_tables()

    # SchedulerConfig默认值
    insert_default_scheduler_config()

    # SystemConfig默认值
    insert_default_system_config()

    # 检查用户
    check_user()

    print('\nDatabase migration completed successfully!')
