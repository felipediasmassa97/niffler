# Backend config can't reference variables, so bucket/key are literal per environment.
# Bucket is created once by infra/bootstrap/bootstrap.sh, not by this project.
terraform {
  backend "s3" {
    bucket       = "niffler-prod-tfstate-309917471802"
    key          = "prod/terraform.tfstate"
    region       = "us-east-2"
    profile      = "niffler-infra"
    use_lockfile = true
  }
}
