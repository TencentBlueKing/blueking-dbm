package handler

import (
	"github.com/Shopify/sarama"
)

func (c *RegisterHandler) Setup(sarama.ConsumerGroupSession) error {
	close(c.Ready)
	return nil
}
