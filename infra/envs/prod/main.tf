module "data_bucket" {
  source = "../../modules/s3_bucket"

  bucket_name = var.data_bucket_name
  tags = {
    Environment = var.environment
    Project     = "niffler"
  }
}

module "streamlit_iam" {
  source = "../../modules/iam"

  user_name  = var.streamlit_user_name
  bucket_arn = module.data_bucket.bucket_arn
  tags = {
    Environment = var.environment
    Project     = "niffler"
  }
}
