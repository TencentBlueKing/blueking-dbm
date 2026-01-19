/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package ginx

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

// BadRequestError ...
const (
	BadRequestError   = "BadRequest"
	UnauthorizedError = "Unauthorized"
	ForbiddenError    = "Forbidden"
	NotFoundError     = "NotFound"
	ConflictError     = "Conflict"
	TooManyRequests   = "TooManyRequests"

	SystemError = "InternalServerError"
)

// SuccessResponse ...
type SuccessResponse struct {
	Data any `json:"data"`
}

// Error ...
type Error struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// ErrorResponse  ...
type ErrorResponse struct {
	Error Error `json:"error"`
}

// SuccessJSONResponse ...
func SuccessJSONResponse(c *gin.Context, data any) {
	c.JSON(http.StatusOK, SuccessResponse{
		Data: data,
	})
}

// SuccessCreateResponse ...
func SuccessCreateResponse(c *gin.Context) {
	c.JSON(http.StatusCreated, nil)
}

// SuccessNoContentResponse ...
func SuccessNoContentResponse(c *gin.Context) {
	c.JSON(http.StatusNoContent, nil)
}

// SuccessFileResponse ...
func SuccessFileResponse(c *gin.Context, contentType string, fileData []byte, fileName string) {
	c.Header(
		"Content-Disposition",
		`attachment; filename=`+fileName,
	)
	c.Data(200, contentType, fileData)
}

// BaseErrorJSONResponse ...
func BaseErrorJSONResponse(c *gin.Context, errorCode, message string, statusCode int) {
	// BaseJSONResponse(c, statusCode, code, message, gin.H{})
	c.JSON(statusCode, ErrorResponse{Error: Error{
		Code:    errorCode,
		Message: message,
	}})
}

// BaseErrorJSONResponseWithData ...
func BaseErrorJSONResponseWithData(
	c *gin.Context,
	errorCode string,
	message string,
	statusCode int,
	data any,
) {
	// BaseJSONResponse(c, statusCode, code, message, gin.H{})
	c.JSON(statusCode, ErrorResponse{Error: Error{
		Code:    errorCode,
		Message: message,
		Data:    data,
	}})
}

// NewErrorJSONResponse ...
func NewErrorJSONResponse(
	errorCode string,
	statusCode int,
) func(c *gin.Context, err error) {
	return func(c *gin.Context, err error) {
		BaseErrorJSONResponse(c, errorCode, err.Error(), statusCode)
	}
}

// BadRequestErrorJSONResponse ...
var (
	BadRequestErrorJSONResponse = NewErrorJSONResponse(BadRequestError, http.StatusBadRequest)
	ForbiddenJSONResponse       = NewErrorJSONResponse(ForbiddenError, http.StatusForbidden)
	UnauthorizedJSONResponse    = NewErrorJSONResponse(UnauthorizedError, http.StatusUnauthorized)
	NotFoundJSONResponse        = NewErrorJSONResponse(NotFoundError, http.StatusNotFound)
	ConflictJSONResponse        = NewErrorJSONResponse(ConflictError, http.StatusConflict)
	TooManyRequestsJSONResponse = NewErrorJSONResponse(TooManyRequests, http.StatusTooManyRequests)
)

// SystemErrorJSONResponse ...
func SystemErrorJSONResponse(c *gin.Context, err error) {
	message := fmt.Sprintf("system error: %s", err.Error())
	BaseErrorJSONResponse(c, SystemError, message, http.StatusInternalServerError)
}
