"""
权限管理Gradio应用
为管理员提供用户权限管理的Web界面
"""

import gradio as gr
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging

from .admin_interface import AdminInterface

logger = logging.getLogger(__name__)


class AdminGradioApp:
    """管理员权限管理Gradio应用"""
    
    def __init__(self):
        """初始化应用"""
        self.admin_interface = AdminInterface()
        self.is_authenticated = False
        
    def create_app(self) -> gr.Blocks:
        """
        创建Gradio应用界面
        
        Returns:
            gr.Blocks: Gradio应用
        """
        with gr.Blocks(title="ChatBI 权限管理系统", theme=gr.themes.Soft()) as app:
            gr.Markdown("# ChatBI 权限管理系统")
            gr.Markdown("管理员可以在此管理用户权限、允许注册的工号等")
            
            # 登录状态
            login_status = gr.State(False)
            
            with gr.Tab("管理员登录"):
                self._create_login_tab(login_status)
            
            with gr.Tab("用户管理") as user_tab:
                self._create_user_management_tab(login_status)
            
            with gr.Tab("权限管理") as permission_tab:
                self._create_permission_management_tab(login_status)
            
            with gr.Tab("工号白名单") as employee_tab:
                self._create_employee_whitelist_tab(login_status)
            
            with gr.Tab("系统统计") as stats_tab:
                self._create_system_stats_tab(login_status)
            
            # 根据登录状态控制标签页可见性
            def update_tabs_visibility(is_logged_in):
                return (
                    gr.update(visible=is_logged_in),  # user_tab
                    gr.update(visible=is_logged_in),  # permission_tab
                    gr.update(visible=is_logged_in),  # employee_tab
                    gr.update(visible=is_logged_in)   # stats_tab
                )
            
            login_status.change(
                update_tabs_visibility,
                inputs=[login_status],
                outputs=[user_tab, permission_tab, employee_tab, stats_tab]
            )
        
        return app
    
    def _create_login_tab(self, login_status):
        """创建登录标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 管理员登录")
                
                employee_id_input = gr.Textbox(
                    label="管理员工号",
                    placeholder="请输入管理员工号"
                )
                
                password_input = gr.Textbox(
                    label="密码",
                    type="password",
                    placeholder="请输入密码"
                )
                
                login_btn = gr.Button("登录", variant="primary")
                login_message = gr.Textbox(
                    label="登录状态",
                    interactive=False,
                    visible=False
                )
                
                def handle_login(employee_id, password):
                    success, message = self.admin_interface.authenticate_admin(employee_id, password)
                    if success:
                        return (
                            True,  # login_status
                            gr.update(value=message, visible=True),  # login_message
                            gr.update(value="", interactive=False),  # employee_id_input
                            gr.update(value="", interactive=False)   # password_input
                        )
                    else:
                        return (
                            False,  # login_status
                            gr.update(value=f"登录失败: {message}", visible=True),  # login_message
                            gr.update(interactive=True),  # employee_id_input
                            gr.update(interactive=True)   # password_input
                        )
                
                login_btn.click(
                    handle_login,
                    inputs=[employee_id_input, password_input],
                    outputs=[login_status, login_message, employee_id_input, password_input]
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 使用说明")
                gr.Markdown("""
                **权限管理系统功能：**
                
                1. **用户管理** - 查看所有用户，启用/禁用用户账户
                2. **权限管理** - 为用户分配和撤销数据库schema权限
                3. **工号白名单** - 管理允许注册的工号列表
                4. **系统统计** - 查看系统使用统计信息
                
                **注意事项：**
                - 只有管理员账户才能访问此系统
                - 请妥善保管管理员账户信息
                - 权限变更会立即生效
                """)
    
    def _create_user_management_tab(self, login_status):
        """创建用户管理标签页"""
        gr.Markdown("### 用户管理")
        
        with gr.Row():
            search_input = gr.Textbox(
                label="搜索用户",
                placeholder="输入工号、邮箱或姓名进行搜索"
            )
            search_btn = gr.Button("搜索")
            refresh_btn = gr.Button("刷新列表")
        
        users_table = gr.Dataframe(
            label="用户列表",
            interactive=False,
            wrap=True
        )
        
        with gr.Row():
            selected_user_id = gr.Textbox(
                label="选中用户ID",
                placeholder="从上表中复制用户ID"
            )
            toggle_status_btn = gr.Button("切换用户状态")
            status_message = gr.Textbox(
                label="操作结果",
                interactive=False
            )
        
        def load_users():
            return self.admin_interface.get_users_list()
        
        def search_users(keyword):
            return self.admin_interface.search_users(keyword)
        
        def toggle_user_status(user_id):
            if not user_id.strip():
                return "请输入用户ID", gr.update()
            
            success, message = self.admin_interface.toggle_user_status(user_id.strip())
            if success:
                return message, load_users()
            else:
                return f"操作失败: {message}", gr.update()
        
        # 初始加载用户列表
        users_table.value = load_users()
        
        # 绑定事件
        search_btn.click(search_users, inputs=[search_input], outputs=[users_table])
        refresh_btn.click(load_users, outputs=[users_table])
        toggle_status_btn.click(
            toggle_user_status,
            inputs=[selected_user_id],
            outputs=[status_message, users_table]
        )
    
    def _create_permission_management_tab(self, login_status):
        """创建权限管理标签页"""
        gr.Markdown("### 权限管理")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 查看用户权限")
                
                user_id_input = gr.Textbox(
                    label="用户ID",
                    placeholder="输入要查看权限的用户ID"
                )
                
                view_permissions_btn = gr.Button("查看权限")
                
                permissions_table = gr.Dataframe(
                    label="用户权限列表",
                    interactive=False,
                    wrap=True
                )
            
            with gr.Column(scale=1):
                gr.Markdown("#### 权限操作")
                
                # 分配权限
                gr.Markdown("**分配权限**")
                assign_user_id = gr.Textbox(
                    label="用户ID",
                    placeholder="要分配权限的用户ID"
                )
                
                available_schemas = self.admin_interface.get_available_schemas()
                schema_dropdown = gr.Dropdown(
                    label="Schema名称",
                    choices=available_schemas,
                    value=available_schemas[0] if available_schemas else None
                )
                
                permission_level_dropdown = gr.Dropdown(
                    label="权限级别",
                    choices=["读取", "写入", "管理"],
                    value="读取"
                )
                
                assign_btn = gr.Button("分配权限", variant="primary")
                
                # 撤销权限
                gr.Markdown("**撤销权限**")
                permission_id_input = gr.Textbox(
                    label="权限ID",
                    placeholder="从权限列表中复制权限ID"
                )
                
                revoke_btn = gr.Button("撤销权限", variant="secondary")
                
                # 操作结果
                permission_message = gr.Textbox(
                    label="操作结果",
                    interactive=False
                )
        
        def view_user_permissions(user_id):
            if not user_id.strip():
                return gr.update()
            return self.admin_interface.get_user_permissions(user_id.strip())
        
        def assign_permission(user_id, schema_name, permission_level):
            if not user_id.strip() or not schema_name:
                return "请填写完整信息", gr.update()
            
            success, message = self.admin_interface.assign_permission(
                user_id.strip(), schema_name, permission_level
            )
            
            if success:
                # 刷新权限列表
                updated_permissions = self.admin_interface.get_user_permissions(user_id.strip())
                return message, updated_permissions
            else:
                return f"分配失败: {message}", gr.update()
        
        def revoke_permission(permission_id):
            if not permission_id.strip():
                return "请输入权限ID", gr.update()
            
            success, message = self.admin_interface.revoke_permission(permission_id.strip())
            return message, gr.update()
        
        # 绑定事件
        view_permissions_btn.click(
            view_user_permissions,
            inputs=[user_id_input],
            outputs=[permissions_table]
        )
        
        assign_btn.click(
            assign_permission,
            inputs=[assign_user_id, schema_dropdown, permission_level_dropdown],
            outputs=[permission_message, permissions_table]
        )
        
        revoke_btn.click(
            revoke_permission,
            inputs=[permission_id_input],
            outputs=[permission_message, permissions_table]
        )
    
    def _create_employee_whitelist_tab(self, login_status):
        """创建工号白名单标签页"""
        gr.Markdown("### 工号白名单管理")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 允许注册的工号列表")
                
                refresh_employees_btn = gr.Button("刷新列表")
                
                employees_table = gr.Dataframe(
                    label="允许注册的工号",
                    interactive=False,
                    wrap=True
                )
            
            with gr.Column(scale=1):
                gr.Markdown("#### 工号管理操作")
                
                # 添加工号
                gr.Markdown("**添加允许注册的工号**")
                new_employee_id = gr.Textbox(
                    label="工号",
                    placeholder="输入要添加的工号"
                )
                
                employee_description = gr.Textbox(
                    label="描述（可选）",
                    placeholder="添加描述信息"
                )
                
                add_employee_btn = gr.Button("添加工号", variant="primary")
                
                # 移除工号
                gr.Markdown("**移除工号**")
                remove_employee_id = gr.Textbox(
                    label="要移除的工号",
                    placeholder="输入要移除的工号"
                )
                
                remove_employee_btn = gr.Button("移除工号", variant="secondary")
                
                # 操作结果
                employee_message = gr.Textbox(
                    label="操作结果",
                    interactive=False
                )
        
        def load_allowed_employees():
            return self.admin_interface.get_allowed_employees()
        
        def add_allowed_employee(employee_id, description):
            if not employee_id.strip():
                return "工号不能为空", gr.update()
            
            success, message = self.admin_interface.add_allowed_employee(
                employee_id.strip(), description.strip()
            )
            
            if success:
                return message, load_allowed_employees()
            else:
                return f"添加失败: {message}", gr.update()
        
        def remove_allowed_employee(employee_id):
            if not employee_id.strip():
                return "工号不能为空", gr.update()
            
            success, message = self.admin_interface.remove_allowed_employee(employee_id.strip())
            
            if success:
                return message, load_allowed_employees()
            else:
                return f"移除失败: {message}", gr.update()
        
        # 初始加载
        employees_table.value = load_allowed_employees()
        
        # 绑定事件
        refresh_employees_btn.click(load_allowed_employees, outputs=[employees_table])
        
        add_employee_btn.click(
            add_allowed_employee,
            inputs=[new_employee_id, employee_description],
            outputs=[employee_message, employees_table]
        )
        
        remove_employee_btn.click(
            remove_allowed_employee,
            inputs=[remove_employee_id],
            outputs=[employee_message, employees_table]
        )
    
    def _create_system_stats_tab(self, login_status):
        """创建系统统计标签页"""
        gr.Markdown("### 系统统计信息")
        
        refresh_stats_btn = gr.Button("刷新统计")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 用户统计")
                user_stats = gr.JSON(
                    label="用户相关统计",
                    value={}
                )
            
            with gr.Column(scale=1):
                gr.Markdown("#### 权限统计")
                permission_stats = gr.JSON(
                    label="权限相关统计",
                    value={}
                )
        
        with gr.Row():
            gr.Markdown("#### 详细统计信息")
            full_stats = gr.JSON(
                label="完整系统统计",
                value={}
            )
        
        def load_system_stats():
            stats = self.admin_interface.get_system_stats()
            
            # 分离用户和权限统计
            user_stats_data = {
                "总用户数": stats.get("总用户数", 0),
                "活跃用户数": stats.get("活跃用户数", 0),
                "管理员数": stats.get("管理员数", 0)
            }
            
            permission_stats_data = {
                "总权限数": stats.get("总权限数", 0),
                "有效权限数": stats.get("有效权限数", 0),
                "允许注册工号数": stats.get("允许注册工号数", 0)
            }
            
            return user_stats_data, permission_stats_data, stats
        
        # 初始加载统计
        initial_stats = load_system_stats()
        user_stats.value = initial_stats[0]
        permission_stats.value = initial_stats[1]
        full_stats.value = initial_stats[2]
        
        # 绑定刷新事件
        refresh_stats_btn.click(
            load_system_stats,
            outputs=[user_stats, permission_stats, full_stats]
        )


def create_admin_app() -> gr.Blocks:
    """
    创建管理员权限管理应用
    
    Returns:
        gr.Blocks: Gradio应用实例
    """
    app = AdminGradioApp()
    return app.create_app()


def launch_admin_app(server_name: str = "127.0.0.1", server_port: int = 7861, 
                    share: bool = False, debug: bool = False):
    """
    启动管理员权限管理应用
    
    Args:
        server_name: 服务器地址
        server_port: 服务器端口
        share: 是否创建公共链接
        debug: 是否启用调试模式
    """
    try:
        app = create_admin_app()
        
        logger.info(f"启动管理员权限管理应用: http://{server_name}:{server_port}")
        
        app.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
            debug=debug,
            show_error=True,
            quiet=False
        )
        
    except Exception as e:
        logger.error(f"启动管理员应用失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动应用
    launch_admin_app(debug=True)