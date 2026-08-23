variable "environment" {
  description = "Environment name (dev/demo/prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "account_id" {
  description = "AWS account ID - used to construct the account-wide execution role ARN"
  type        = string
  default     = "309917471802"
}

variable "data_bucket_name" {
  description = "This environment's S3 data bucket name"
  type        = string
}

variable "streamlit_user_name" {
  description = "This environment's Streamlit app IAM user name"
  type        = string
}
