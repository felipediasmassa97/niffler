output "data_bucket_name" {
  value = module.data_bucket.bucket_name
}

output "data_bucket_arn" {
  value = module.data_bucket.bucket_arn
}

output "streamlit_user_name" {
  value = module.streamlit_iam.user_name
}

output "streamlit_access_key_id" {
  value = module.streamlit_iam.access_key_id
}

output "streamlit_secret_access_key" {
  value     = module.streamlit_iam.secret_access_key
  sensitive = true
}
