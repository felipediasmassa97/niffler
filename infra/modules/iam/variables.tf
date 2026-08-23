variable "user_name" {
  description = "IAM user name for this environment's Streamlit app identity (e.g. niffler-streamlit-app-dev)"
  type        = string
}

variable "bucket_arn" {
  description = "ARN of this environment's data bucket"
  type        = string
}

variable "snapshot_prefix" {
  description = "S3 key prefix the app identity is allowed to read"
  type        = string
  default     = "snapshots"
}

variable "tags" {
  description = "Tags applied to the IAM user"
  type        = map(string)
  default     = {}
}
