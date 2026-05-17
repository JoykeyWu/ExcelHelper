# 计算公式 & 指标口径

## 基础指标

### 总时长
```
总时长 = SUM(duration_min)
```
某个维度下所有记录的使用时长之和

### 人均时长
```
人均时长 = SUM(duration_min) / COUNT(DISTINCT user_id)
```
总时长除以该维度下的去重用户数。注意分母是去重用户数，不是记录数

### 参与人数
```
参与人数 = COUNT(DISTINCT user_id)
```
该维度下去重用户数。等价于有多少个不同的人参与了

### 日均时长
```
日均时长 = SUM(duration_min) / COUNT(DISTINCT date)
```
总时长除以有数据的天数。如果维度是"日期"，则不需要此指标

## 高级指标

### 参与率
```
参与率 = 该圈参与人数 / 全部用户数 × 100%
```
需要先计算出全部用户数（从 user_mapping 表获取总行数），再计算每个圈子的参与率

### 人均使用天数
```
人均使用天数 = COUNT(DISTINCT date, user_id) / COUNT(DISTINCT user_id)
```
该维度下每人平均来了几天

### 部门贡献度
```
部门贡献度 = 该部门总时长 / 所有部门总时长 × 100%
```

## 分组聚合时的默认行为

- 用户说"按XX分组求总和" → groupby_agg，aggfunc 用 ["sum"]
- 用户说"求平均" → aggfunc 用 ["mean"]
- 用户说"求人数" → 对 user_id 用 "nunique"
- 用户说"各项数据"或"汇总统计" → aggfunc 用 ["sum", "mean", "count"]
- 分组后务必重命名列（rename），把 machine name 变成中文可读名称
