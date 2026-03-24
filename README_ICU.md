# TrainingEdge — Intervals.icu Edition

基于 [sisjune/training-edge](https://github.com/sisjune/training-edge) 改造，将数据源从 Garmin Connect 替换为 Intervals.icu，并集成 Oura Ring 健康数据。

## 主要改动

| 功能 | 原版 | 改造版 |
|------|------|--------|
| 数据源 | Garmin Connect | **Intervals.icu** |
| 认证方式 | Session Cookie | **HTTP Basic Auth (API Key)** |
| 健康数据 | Garmin 健康指标 | **Oura Ring (通过 Intervals)** |
| 晨间报告 | 无 | **Oura 健康综述** |
| 路径配置 | 硬编码 | **环境变量 / NAS 适配** |

## 环境变量配置

创建 `.env` 文件：

```bash
# 必需：Intervals.icu API 配置
INTERVALS_API_KEY=your_api_key_here
INTERVALS_ATHLETE_ID=0

# 可选：路径配置（NAS 适配）
REPORTS_DIR=./reports                    # 报告输出目录
TRAININGEDGE_STATE_DIR=./state           # 数据库目录
TRAININGEDGE_DB_PATH=./state/training_edge.db

# 可选：Web 访问密码
TRAININGEDGE_PASSWORD=your_password

# 可选：自动同步间隔（小时）
TRAININGEDGE_SYNC_INTERVAL_HOURS=6
```

## API Key 获取

1. 登录 [Intervals.icu](https://intervals.icu)
2. 进入 Settings → Developer
3. 生成 API Key

## 启动应用

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移（如使用旧数据库）
python scripts/migrate_db.py

# 启动服务
python -m api.app
```

## API 端点

### 同步数据
```bash
# 全量同步
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"type": "all", "days": 7}'

# 仅同步 wellness（含 Oura）
curl -X POST http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{"type": "wellness", "days": 14}'
```

### Oura 健康报告
```bash
# 获取晨间健康综述
curl http://localhost:8000/api/oura/morning-report

# 获取文本格式报告
curl http://localhost:8000/api/oura/morning-report/text

# 获取趋势数据
curl http://localhost:8000/api/oura/trend?days=7
```

### Intervals.icu 专用端点
```bash
# 健康检查
curl http://localhost:8000/api/v1/icu/health

# 同步活动
curl -X POST http://localhost:8000/api/v1/icu/sync/activities?days=7

# 同步 wellness
curl -X POST http://localhost:8000/api/v1/icu/sync/wellness?days=14
```

## Oura 数据字段

通过 Intervals.icu wellness 接口同步的 Oura Ring 数据：

| 字段 | 来源 | 说明 |
|------|------|------|
| `readiness` | Oura readinessScore | 恢复分数 (0-100) |
| `hrv` | Oura hrv_rmssd | 心率变异性 (ms) |
| `body_temp_deviation` | Oura body_temp_deviation | 体温偏差 (°C) |
| `resting_hr` | Oura restingHR | 静息心率 |
| `sleep_score` | Oura sleepScore | 睡眠评分 |

## 文件结构

```
training-edge/
├── engine/
│   ├── config.py           # 配置管理（含 NAS 路径）
│   ├── mapping.py          # 数据映射器（Intervals → 内部格式）
│   ├── sync_intervals.py   # Intervals.icu 同步模块
│   ├── oura_report.py      # Oura 健康报告生成器
│   └── database.py         # 数据库层（已添加 Oura 字段）
├── api/
│   ├── app.py              # 主应用（已集成新模块）
│   └── api_icu.py          # Intervals.icu 专用 API
├── scripts/
│   └── migrate_db.py       # 数据库迁移脚本
└── .env.example            # 环境变量模板
```

## 数据流

```
Oura Ring → Intervals.icu → TrainingEdge
                ↓
         ┌──────┴──────┐
         ↓             ↓
    /activities    /wellness
         ↓             ↓
    activities      wellness
    表              表 (含 Oura)
         ↓             ↓
         └──────┬──────┘
                ↓
         fitness_history
         (CTL/ATL/TSB)
                ↓
         Oura 晨间报告
```

## 注意事项

1. **Intervals.icu 必须先同步 Oura**：确保在 Intervals 设置中连接了 Oura Ring
2. **API Key 安全**：不要提交 `.env` 文件到 Git
3. **数据库迁移**：升级旧数据库需运行 `migrate_db.py`
4. **FIT 文件**：不再下载，所有指标来自 Intervals 计算结果

## 故障排查

```bash
# 检查 Intervals 配置
curl http://localhost:8000/api/v1/icu/config

# 检查健康状态
curl http://localhost:8000/api/health

# 查看数据库内容
sqlite3 state/training_edge.db "SELECT date, readiness, hrv FROM wellness ORDER BY date DESC LIMIT 5;"
```
