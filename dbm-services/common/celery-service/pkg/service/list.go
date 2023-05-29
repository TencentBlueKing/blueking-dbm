package service

import "fmt"

func List() error {
	err := Init()
	if err != nil {
		return err
	}
	fmt.Printf("%v\n", r.Routes())
	return nil
}
