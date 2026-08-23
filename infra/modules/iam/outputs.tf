output "user_name" {
  description = "The Streamlit app identity's IAM user name"
  value       = aws_iam_user.streamlit_app.name
}

output "access_key_id" {
  description = "Access key ID for the Streamlit app identity"
  value       = aws_iam_access_key.streamlit_app.id
}

output "secret_access_key" {
  description = "Secret access key for the Streamlit app identity - copy into secrets.toml / Streamlit Cloud Secrets, never commit"
  value       = aws_iam_access_key.streamlit_app.secret
  sensitive   = true
}
