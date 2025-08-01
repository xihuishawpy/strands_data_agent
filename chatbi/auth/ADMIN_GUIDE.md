# ChatBI 权限管理系统使用指南

## 概述

ChatBI 权限管理系统为管理员提供了一个基于Web的界面，用于管理用户权限、允许注册的工号列表以及查看系统统计信息。

## 启动管理界面

### 方法1: 使用启动脚本

```bash
python start_admin_app.py
```

### 方法2: 直接运行模块

```bash
python -m chatbi.auth.gradio_admin_app
```

### 方法3: 在代码中启动

```python
from chatbi.auth import launch_admin_app

launch_admin_app(
    server_name="127.0.0.1",
    server_port=7861,
    share=False,
    debug=True
)
```

启动后，在浏览器中访问 `http://127.0.0.1:7861` 即可使用管理界面。

## 功能说明

### 1. 管理员登录

- **功能**: 验证管理员身份
- **要求**: 必须使用具有管理员权限的账户登录
- **输入**: 管理员工号和密码
- **注意**: 只有 `is_admin=True` 的用户才能登录管理界面

### 2. 用户管理

#### 2.1 查看用户列表
- 显示所有注册用户的基本信息
- 包含用户ID、工号、邮箱、姓名、状态、权限数量等
- 支持按工号、邮箱、姓名搜索用户

#### 2.2 用户状态管理
- **启用/禁用用户**: 切换用户的活跃状态
- **限制**: 管理员不能禁用自己的账户
- **效果**: 禁用的用户无法登录系统

### 3. 权限管理

#### 3.1 查看用户权限
- 输入用户ID查看该用户的所有权限
- 显示Schema名称、权限级别、授权人、授权时间等
- 区分有效和无效权限

#### 3.2 分配权限
- **用户ID**: 要分配权限的用户ID
- **Schema名称**: 从可用Schema列表中选择
- **权限级别**: 
  - `读取`: 只能执行SELECT查询
  - `写入`: 可以执行INSERT、UPDATE、DELETE操作
  - `管理`: 拥有完全访问权限，包括DDL操作

#### 3.3 撤销权限
- 输入权限ID撤销特定权限
- 权限ID可以从权限列表中复制获得
- 撤销后立即生效

### 4. 工号白名单管理

#### 4.1 查看允许注册的工号
- 显示所有允许注册的工号列表
- 包含工号、添加人、添加时间、描述等信息

#### 4.2 添加允许注册的工号
- **工号**: 要添加的员工工号
- **描述**: 可选的描述信息
- **效果**: 只有在白名单中的工号才能注册账户

#### 4.3 移除工号
- 从白名单中移除指定工号
- 移除后该工号无法注册新账户
- 不影响已注册的用户

### 5. 系统统计

#### 5.1 用户统计
- 总用户数
- 活跃用户数
- 管理员数

#### 5.2 权限统计
- 总权限数
- 有效权限数
- 允许注册工号数

#### 5.3 详细统计
- 完整的系统统计信息
- 包含统计时间戳

## 使用流程示例

### 新用户注册流程

1. **添加工号到白名单**
   - 在"工号白名单"标签页中添加新员工的工号
   - 填写描述信息（可选）

2. **用户自行注册**
   - 用户使用白名单中的工号进行注册
   - 注册成功后账户默认为普通用户

3. **分配数据库权限**
   - 在"权限管理"标签页中为新用户分配Schema权限
   - 根据用户职责选择合适的权限级别

### 权限调整流程

1. **查看当前权限**
   - 在"权限管理"标签页中输入用户ID查看当前权限

2. **调整权限**
   - 分配新的Schema权限
   - 撤销不再需要的权限
   - 调整权限级别

3. **验证权限**
   - 用户重新登录后新权限生效
   - 可以通过系统统计查看权限变更

## 安全注意事项

### 1. 管理员账户安全
- 使用强密码保护管理员账户
- 定期更换管理员密码
- 不要共享管理员账户

### 2. 权限分配原则
- **最小权限原则**: 只分配用户工作所需的最小权限
- **定期审查**: 定期检查和清理不必要的权限
- **职责分离**: 避免给单个用户过多权限

### 3. 工号白名单管理
- 及时添加新员工工号
- 员工离职时及时移除工号和禁用账户
- 定期审查白名单的准确性

## 故障排除

### 1. 无法登录管理界面
- 检查账户是否具有管理员权限 (`is_admin=True`)
- 确认工号和密码正确
- 检查账户是否被禁用

### 2. 权限分配失败
- 确认用户ID正确
- 检查Schema名称是否存在
- 确认管理员已登录

### 3. 界面无法访问
- 检查服务是否正常启动
- 确认端口7861未被占用
- 检查防火墙设置

## API参考

### AdminInterface类主要方法

```python
# 管理员认证
authenticate_admin(employee_id: str, password: str) -> Tuple[bool, str]

# 用户管理
get_users_list() -> pd.DataFrame
toggle_user_status(user_id: str) -> Tuple[bool, str]
search_users(keyword: str) -> pd.DataFrame

# 权限管理
get_user_permissions(user_id: str) -> pd.DataFrame
assign_permission(user_id: str, schema_name: str, permission_level: str) -> Tuple[bool, str]
revoke_permission(permission_id: str) -> Tuple[bool, str]

# 工号白名单管理
get_allowed_employees() -> pd.DataFrame
add_allowed_employee(employee_id: str, description: str) -> Tuple[bool, str]
remove_allowed_employee(employee_id: str) -> Tuple[bool, str]

# 系统统计
get_system_stats() -> Dict[str, Any]
```

## 扩展开发

如果需要扩展管理界面功能，可以：

1. **继承AdminInterface类**添加新的管理方法
2. **修改AdminGradioApp类**添加新的界面组件
3. **创建新的标签页**实现特定功能
4. **集成外部系统**如LDAP、SSO等

## 技术支持

如有问题或建议，请联系开发团队或查看项目文档。