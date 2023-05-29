package kafka

import (
	"dbm-services/redis/db-tools/dbmon/mylog"
	"fmt"
	"io/ioutil"
	"log"
	"strings"
	"time"

	"github.com/Shopify/sarama"
)

// KafkaClient KafkaClient
// https://git..com/scc-gamedba2/dbmonitor/xml_server_kafka/blob/master/client/main.go
func KafkaClient(hosts, topic, user, password, fname string) error {
	inputBytes, err := ioutil.ReadFile(fname)
	if err != nil {
		log.Print(err)
		return err
	}

	config := sarama.NewConfig()
	config.Producer.Retry.Max = 1
	config.Producer.RequiredAcks = sarama.WaitForAll

	config.Metadata.Full = true
	config.Version = sarama.V3_2_3_0
	config.ClientID = "bk-dbmon"
	config.Metadata.Full = true
	config.Net.SASL.Enable = true
	config.Net.SASL.User = user
	config.Net.SASL.Password = password
	config.Net.SASL.Handshake = true
	// 最大100MB
	config.Producer.MaxMessageBytes = 100000000
	config.Net.SASL.SCRAMClientGeneratorFunc = func() sarama.SCRAMClient {
		return &XDGSCRAMClient{
			HashGeneratorFcn: SHA512}
	}
	config.Net.SASL.Mechanism = sarama.SASLTypeSCRAMSHA512
	config.Producer.Return.Successes = true
	config.Producer.Timeout = 6 * time.Second

	var producer sarama.SyncProducer
	for i := 0; i < 10; i++ {
		producer, err = sarama.NewSyncProducer(strings.Split(hosts, ","), config)
		if err != nil {
			mylog.Logger.Error(fmt.Sprintf("connection producer failed %s:%+v", hosts, err))
			time.Sleep(time.Second * 2)
			continue
		}
		break
	}
	defer producer.Close()
	srcValue := inputBytes
	msg := &sarama.ProducerMessage{
		Topic: topic,
		Value: sarama.ByteEncoder(srcValue),
	}
	if part, offset, err := producer.SendMessage(msg); err != nil {
		mylog.Logger.Error(fmt.Sprintf("send file(%s) err=%s", fname, err))
	} else {
		mylog.Logger.Info(fmt.Sprintf("send succ,partition=%d, offset=%d", part, offset))
	}
	return err
}
