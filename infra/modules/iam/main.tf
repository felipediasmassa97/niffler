# Least-privilege, read-only IAM identity for one environment's Streamlit app instance.
# Instantiated once per environment (see infra/envs/*/main.tf) so a leaked dev credential
# can never read prod data - each instance only ever sees its own bucket_arn.

resource "aws_iam_user" "streamlit_app" {
  name = var.user_name
  tags = var.tags
}

data "aws_iam_policy_document" "read_snapshots" {
  statement {
    sid       = "ListSnapshotsPrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.snapshot_prefix}/*"]
    }
  }

  statement {
    sid       = "ReadSnapshotObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/${var.snapshot_prefix}/*"]
  }
}

resource "aws_iam_user_policy" "read_snapshots" {
  name   = "${var.user_name}-read-snapshots"
  user   = aws_iam_user.streamlit_app.name
  policy = data.aws_iam_policy_document.read_snapshots.json
}

resource "aws_iam_access_key" "streamlit_app" {
  user = aws_iam_user.streamlit_app.name
}

# fixit provision user with less permissions than AdministratorAccess for fmassa
