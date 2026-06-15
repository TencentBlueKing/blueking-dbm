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

package handler

// ConfirmFunc prompts the user and returns true when an operation may proceed.
type ConfirmFunc func(prompt string) bool

// ListOptions contains list command filters.
type ListOptions struct {
	BkBizID       int
	BkCloudID     int
	ClusterID     int
	ClusterName   string
	SwitchVersion string
	Status        string
	Output        string
	OutputFile    string
}

// AddOptions contains add command arguments.
type AddOptions struct {
	BkBizID       int
	BkCloudID     int
	ClusterID     int
	ClusterName   string
	SwitchVersion string
	Status        string
}

// UpdateOptions contains update command query and set arguments.
type UpdateOptions struct {
	ID            int
	BkBizID       int
	BkCloudID     int
	ClusterID     int
	ClusterName   string
	SwitchVersion string
	Status        string
	Yes           bool
	Confirm       ConfirmFunc
}

// DeleteOptions contains delete command query arguments.
type DeleteOptions struct {
	ID          int
	BkBizID     int
	BkCloudID   int
	ClusterID   int
	ClusterName string
	Yes         bool
	Confirm     ConfirmFunc
}

type queryOptions struct {
	ID          int
	BkBizID     int
	BkCloudID   int
	ClusterID   int
	ClusterName string
}

type commonQueryArgs struct {
	ID          *uint
	BkBizID     *int
	BkCloudID   *int
	ClusterID   *int
	ClusterName *string
}
