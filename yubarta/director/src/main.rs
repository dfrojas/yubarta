use tokio;
use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::config::ClientConfig;
use rdkafka::Message;
use serde_json::Value;
use futures::StreamExt;

struct Director {
    kafka_broker: String,
    topic: String,
}

impl Director {
    fn new(kafka_broker: String, topic: String) -> Self {
        Self {
            kafka_broker,
            topic,
        }
    }

    async fn run(&self) -> Result<(), Box<dyn std::error::Error>> {
        println!("Running director");
        
        let consumer: StreamConsumer = ClientConfig::new()
            .set("group.id", "director-group")
            .set("bootstrap.servers", &self.kafka_broker)
            .set("enable.partition.eof", "false")
            .set("session.timeout.ms", "6000")
            .set("enable.auto.commit", "true")
            .set("auto.offset.reset", "earliest")
            .create()?;

        consumer.subscribe(&[&self.topic])?;

        let mut message_stream = consumer.stream();
        
        while let Some(message) = message_stream.next().await {
            match message {
                Ok(msg) => {
                    // TODO: Test performance with batches with a single session.
                    println!("Message: {:?}", msg);
                    
                    // Parse the incoming JSON message
                    if let Some(payload) = msg.payload() {
                        if let Ok(json_value) = serde_json::from_slice::<Value>(payload) {
                            println!("Parsed JSON: {:?}", json_value);
                            
                            // TODO: Implement alert processing logic
                            // let alert = AlertKafkaMessage::from_json(json_value)?;
                            // let alert_repository = SqlAlchemyAlarmRepository::new(session);
                            // AlertController::new(alert_repository).process_alert(alert).await?;
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Error receiving message: {:?}", e);
                }
            }
        }

        Ok(())
    }

    // fn process_message(&self, message: &Value) -> HashMap<String, Value> {
    //     // Process the incoming message and return structured alarm data
    //     HashMap::new()
    // }

    // fn should_execute_remediation(&self, alarm_data: &HashMap<String, Value>) -> bool {
    //     // Decision logic to determine if remediation should be executed
    //     true
    // }

    // async fn execute_remediation(&self, alarm_data: &HashMap<String, Value>) -> Result<(), Box<dyn std::error::Error>> {
    //     // Logic to execute remediation
    //     Ok(())
    // }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // TODO: start_mappers();
    let director = Director::new(
        "kafka:9092".to_string(),
        "yubarta.alerts".to_string()
    );
    
    director.run().await?;
    
    Ok(())
}
