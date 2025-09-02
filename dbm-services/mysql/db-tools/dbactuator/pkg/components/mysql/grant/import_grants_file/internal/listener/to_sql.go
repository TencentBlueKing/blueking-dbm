package listener

func (c *PrivListener) ToSql() string {
	switch c.StatementType {
	case PrivStatementCreate:
		return c.createToSql()
	default:
		return c.grantToSql()
	}
}
