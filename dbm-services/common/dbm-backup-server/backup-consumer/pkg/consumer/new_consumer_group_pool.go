package consumer

import (
	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"

	"github.com/Shopify/sarama"
)

func NewConsumerGroupPool() ([]sarama.ConsumerGroup, error) {
	err := queryMeta()
	if err != nil {
		return nil, err
	}

	var pool []sarama.ConsumerGroup
	for i := 0; i < config.MetaInfo.StorageConfig.Partition; i++ {
		g, err := newConsumerGroup()
		if err != nil {
			return nil, err
		}
		pool = append(pool, g)
	}
	return pool, nil
}
