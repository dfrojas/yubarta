# Yubarta control host (Debian/Ubuntu VM). Fill backend as needed.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "ami" { type = string }
variable "instance_type" { type = string; default = "t3.small" }
variable "key_name" { type = string }
variable "subnet_id" { type = string }
variable "db_url" { type = string; sensitive = true }

resource "aws_instance" "yubarta_control" {
  ami           = var.ami
  instance_type = var.instance_type
  key_name      = var.key_name
  subnet_id     = var.subnet_id
  tags = { Name = "yubarta-control" }
}

output "control_public_ip" {
  value = aws_instance.yubarta_control.public_ip
}
