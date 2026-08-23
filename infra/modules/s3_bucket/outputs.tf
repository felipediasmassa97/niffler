output "bucket_name" {
  description = "The bucket's name"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "The bucket's ARN"
  value       = aws_s3_bucket.this.arn
}
