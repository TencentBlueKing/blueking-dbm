package impl

// SQLResultRow 一行查询结果, 列名 -> 列值
//
//	{
//	  COLNAME1: COLVALUE1,
//	  COLNAME2: COLVALUE2,
//	}
type SQLResultRow map[string]interface{}

// SQLResultRows 一个 SELECT 的全部行
//
//	[
//	  {...}, # row1
//	  {...}, # row2
//	]
type SQLResultRows []SQLResultRow
