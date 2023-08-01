package service

import "fmt"

func List() {
	Init()
	fmt.Printf("%v\n", r.Routes())
}
