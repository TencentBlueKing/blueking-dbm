# dbactuator mysql backup-database-table

## 备份库表


### 原始payload
```
{
    "extend": {
        "host": "127.0.0.1",
        "port": 3306,
        "regex": "^(?!db1)db.*\.t)"
    }
}

```