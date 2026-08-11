package handler

import (
	"github.com/Shopify/sarama"
)

func (c *RegisterHandler) Cleanup(sarama.ConsumerGroupSession) error {
	return nil
}
