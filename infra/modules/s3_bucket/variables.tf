variable "bucket_name" {
  description = "Globally-unique S3 bucket name"
  type        = string
}

variable "noncurrent_version_expiration_days" {
  description = "Days to keep noncurrent object versions before expiring them"
  type        = number
  default     = 90
}

variable "tags" {
  description = "Tags applied to the bucket"
  type        = map(string)
  default     = {}
}
