# Multi-Role Calculator 使用指南

## 一、启动

```powershell
cd C:\Users\lyi\Desktop\deepseek-v4
python server.py
```

浏览器访问 **http://localhost:8080**

按 `Ctrl+C` 停止服务。

---

## 二、角色与权限速查

| 角色 | 可用运算按钮 | 管理功能 | 篡改规则 |
|------|-------------|---------|---------|
| guest（游客） | `+` `−` | 无 | 无 |
| member（会员） | `+` `−` `×` `÷` | 无 | 无 |
| admin（管理员） | `+` `−` `×` `÷` | 升降级用户、封禁/解封 | 无 |
| superadmin（超管） | `+` `−` `×` `÷` | 全部管理能力 | 可篡改数学规则 |

**默认超管账号**：用户名 `root`，密码 `root123`（系统首次启动自动创建）

---

## 三、快速上手

### 第 1 步：登录超管

1. 打开 `http://localhost:8080`，看到登录页
2. 输入用户名 `root`，密码 `root123`
3. 点击 Sign In

登录后你会看到：
- 顶部：用户名 + 角色徽章（`SUPERADMIN`）
- 计算器：全部运算按钮可用
- 最近计算记录（初始为空）
- 用户管理面板：列出所有用户
- 规则篡改面板：可设置数学覆盖规则

### 第 2 步：注册一个游客

1. 点击右上角 Sign Out 退出
2. 切换到 **Register** 标签
3. 输入用户名 `alice`，密码 `pass123`
4. 确认密码后点击 Create Account
5. 注册成功后会看到绿色提示，自动切回 Login 标签

### 第 3 步：体验权限隔离

用 `alice` / `pass123` 登录：
- 计算器只显示 `+` 和 `−` 按钮可用
- `×` 和 `÷` 按钮为灰色（禁用状态）
- 界面底部没有管理面板和规则面板

计算 `3 + 4` → 正常得到 `7`。操作按钮只有加减可用，乘除按钮灰色不可点击。即使通过浏览器开发者工具强制发送乘法请求，后端也会返回 `"操作不允许"` 的拒绝提示。

---

## 四、管理面板（admin / superadmin）

用 `root` 登录后，在"User Management"面板中可以看到所有用户列表。

### 升级/降级

每个用户行右侧有一组按钮：
- **Guest**：将用户降为游客
- **Member**：将用户升级为会员
- **Admin**：（仅 superadmin 可见）将用户升级为管理员

点击后即刻生效，系统弹出绿色成功提示。

### 封禁/解封

- **Ban**：封禁用户（封禁后该用户无法登录，提示"账号已被封禁"）
- **Unban**：解除封禁

操作会弹出确认对话框（Ban），确认后即时生效。

### 权限限制

- admin 只能操作 guest 和 member 角色的用户
- admin 不能修改其他 admin 或 superadmin
- superadmin 可以操作所有用户（但不能 Ban 自己）

---

## 五、规则篡改（superadmin 专属）

用 `root` 登录后在"Rule Tampering"面板操作。

### 添加篡改规则

1. 在面板输入框中填入：
   - `a`：左操作数（如 `2`）
   - 运算符下拉框：选 `+`
   - `b`：右操作数（如 `2`）
   - `result`：篡改后的结果（如 `5`）
2. 点击 **Override** 按钮

效果示例：
> 设置 `2 + 2 = 5` 后
> - alice（guest）登录计算 `2 + 2`，显示结果为 `5`
> - 结果下方出现黄色警告 "⚠ Result modified by superadmin rule"
> - 计算历史中该条记录标记为 `[tampered]`
> - 界面不提示任何"被篡改"的线索（除规则面板本身），仿佛数学本该如此

### 删除规则

在规则列表中点击对应行的 **Delete** 按钮即可删除。

### 规则生命周期

- 规则存储在内存中
- **服务器重启后所有规则清空**，恢复真实数学结果
- 规则对所有用户（包括 guest）立即生效

---

## 六、验收场景（逐一验证）

### 场景 A：角色权限隔离

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | 注册 `alice`，登录 | 计算器只有 `+` `−` 按钮 |
| 2 | 用 `root` 登录，在管理面板将 alice 升级为 member | 提示 "Role updated" |
| 3 | `alice` 退出重新登录 | 现在可以看到 `×` `÷` 按钮 |
| 4 | `alice` 计算 `6 × 7` | 结果为 `42` |

### 场景 B：账号封禁

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | `root` 在管理面板点击 alice 的 **Ban** | 确认后提示 "User banned" |
| 2 | `alice` 尝试登录 | 显示 "Account has been banned" |
| 3 | `root` 点击 alice 的 **Unban** | 提示 "User unbanned" |
| 4 | `alice` 重新登录 | 登录成功 |

### 场景 C：数学规则篡改

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | `root` 在规则面板设置 `2 + 2 = 5` | 规则列表出现 `2 + 2 = 5` |
| 2 | 注册 `bob`（guest），登录后计算 `2 + 2` | 结果为 `5`，显示 tampered 标记 |
| 3 | `root` 点击该规则的 **Delete** | 规则列表清空 |
| 4 | `bob` 再次计算 `2 + 2` | 结果恢复为 `4`，无 tampered 标记 |

### 场景 D：越权防御

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| 1 | `bob`（guest）登录 | 计算器无 `×` 按钮 |
| 2 | F12 打开开发者工具 → Console | 执行越权请求 |
| 3 | 发送：`fetch('/api/calculate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({a:8,op:'*',b:7})}).then(r=>r.json()).then(console.log)` | 返回 `{error: "Operation '*' is not allowed for role 'guest'"}`，页面弹出红色错误提示 "Operation '*' is not allowed for role 'guest'" |

---

## 七、API 接口表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/register` | 公开 | 注册（`{username, password}`）→ 默认 guest |
| POST | `/api/login` | 公开 | 登录（`{username, password}`）→ 返回用户信息 + Set-Cookie |
| POST | `/api/logout` | 登录 | 登出，清除 Cookie |
| GET | `/api/me` | 登录 | 获取当前用户信息 |
| POST | `/api/calculate` | 登录 | 计算 `{a, op, b}`，op 为 `+ - * /` |
| GET | `/api/history` | 登录 | 获取最近 10 条计算历史 |
| GET | `/api/users` | admin+ | 列出所有用户 |
| POST | `/api/users/role` | admin+ | 修改角色 `{user_id, role}`（role: guest/member/admin） |
| POST | `/api/users/ban` | admin+ | 封禁用户 `{user_id}` |
| POST | `/api/users/unban` | admin+ | 解封用户 `{user_id}` |
| GET | `/api/rules` | superadmin | 列出所有篡改规则 |
| POST | `/api/rules` | superadmin | 添加规则 `{a, op, b, result}` |
| DELETE | `/api/rules/{id}` | superadmin | 删除指定规则 |

---

## 八、数据说明

- 数据库文件：`calc.db`（SQLite），位于项目根目录
- 用户密码使用 sha256 + 随机 salt 哈希存储
- 计算历史每个用户保留最近 10 条
- 篡改规则在内存中存储，重启服务器后清空
- 删除 `calc.db` 文件后重启即恢复初始状态（仅 root 账号）
