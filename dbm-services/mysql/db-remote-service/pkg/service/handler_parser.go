package service

//type parseRequest struct {
//	Statements string `form:"statements" json:"statements"`
//}

//// parseHandler parser 服务
//func parseHandler(c *gin.Context) {
//	var req parseRequest
//	if err := c.ShouldBindJSON(&req); err != nil {
//		c.JSON(
//			http.StatusBadRequest, gin.H{
//				"code": 1,
//				"data": "",
//				"msg":  err.Error(),
//			},
//		)
//		return
//	}
//
//	resp, err := parser.Parse(req.Statements)
//	if err != nil {
//		c.JSON(
//			http.StatusInternalServerError, gin.H{
//				"code": 1,
//				"data": "",
//				"msg":  err.Error(),
//			},
//		)
//	}
//
//	c.JSON(
//		http.StatusOK, gin.H{
//			"code": 0,
//			"data": resp,
//			"msg":  "",
//		},
//	)
//}
