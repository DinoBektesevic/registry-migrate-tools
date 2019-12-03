#!/usr/bin/env python3
import boto3
import botocore
import os

splashMsg = \
"""
The following script will help you set up correct AWS credentials.

You should have received a strip of paper containing the following
information:

     Credentials          | Example
    ----------------------|-------------------------
    Login name            | aws-lsst##
    Password              | OUh13EXMPL
    AWS Access Key ID     | AKIAIOSFODNN7EXAMPLE
    AWS Secret Access Key | wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

Please input the AWS Access Key ID and AWS Secret Access Key when
prompted.
================================================================================
"""


def validate(accessKeyId, secretAccessKey):
    """
    Validates that given credentials are correct by simulating
    AWS Security Token Service policy"s access to Put, Get and
    Delete Object operations in a test bucket.

    Parameters
    ----------
    accessKeyId : AWS Access Key ID
    secretAccessKey : AWS Secret Access Key

    Returns
    -------
    validated : True when all validation tests pass, False otherwise.

    Notes
    -----
    Credentials are valid only if the set of minimal Bucket
    operations required for execution pass. These are:
        s3:PutObject
        s3:GetObject
        s3:DeleteObject
        s3:GetBucketLocation
        s3:ListBucket
    """
    iam = boto3.client("iam",
                       aws_access_key_id=accessKeyId,
                       aws_secret_access_key=secretAccessKey)
    sts = boto3.client("sts",
                       aws_access_key_id=accessKeyId,
                       aws_secret_access_key=secretAccessKey)

    # Get the arn represented by the currently configured credentials
    # this can still fail if credentials are not conforming to requirements
    # (char count, type, etc..)
    try:
        arn = sts.get_caller_identity()["Arn"]
    except botocore.exceptions.ClientError as e:
        print("Incorrect credentials: ", e.response["Error"]["Code"])
        return False

    # Create an arn representing the objects in a bucket
    bucket_objects_arn = "arn:aws:s3:::%s/*" % "my-test-bucket"

    # Run the policy simulation for the basic s3 operations
    results = iam.simulate_principal_policy(
        PolicySourceArn=arn,
        ResourceArns=[bucket_objects_arn],
        ActionNames=["s3:PutObject", "s3:GetObject", "s3:DeleteObject",
                     "s3:GetBucketLocation", "s3:ListBucket"]
    )

    # credentials are valid only when all of the required actions
    # are allowed.
    valid = True
    for result in results["EvaluationResults"]:
        print("%s - %s" % (result["EvalActionName"], result["EvalDecision"]))
        valid = valid and (result["EvalDecision"].lower() == "allowed")

    return valid


def requestAndValidateCredentials():
    """
    Requests the credentials from the user and validates them.
    If unsuccessful it requests new credentials from the user.
    Stops when given credentials pass validation.
    """
    validated = False
    while not validated:
        accessKeyId = input("Input AWS Access Key ID: ").strip()
        secretAccessKey = input("Input AWS Secret Access Key: ").strip()
        validated = validate(accessKeyId, secretAccessKey)
        print()

    return accessKeyId, secretAccessKey


def createCondorFiles(accessKeyId, secretAccessKey):
    """
    Creates publicKeyFile and privateKeyFile in ~/.condor.
    Sets 600 permissions on the files.

    Parameters
    ----------
    accessKeyId : AWS Access Key ID
    secretAccessKey : AWS Secret Access Key
    """
    rootDir = os.path.expanduser("~/.condor")
    pairs = ({"path": os.path.join(rootDir, "publicKeyFile"), "key": accessKeyId},
             {"path": os.path.join(rootDir, "privateKeyFile"), "key": secretAccessKey})

    for pair in pairs:
        with open(pair["path"], "w") as credFile:
            credFile.write(pair["key"])
            print(f"Created {pair['path']}")
        os.chmod(pair["path"], 0o600)


def exportCredToEnv(accessKeyId, secretAccessKey):
    """
    Sets environmental variables AWS_ACCESS_KEY_ID and
    AWS_SECRET_ACCESS_KEY.

    Parameters
    ----------
    accessKeyId : AWS Access Key ID
    secretAccessKey : AWS Secret Access Key
    """
    os.environ["AWS_ACCESS_KEY_ID"] = accessKeyId
    print("Exported AWS_ACCESS_KEY_ID to environment variables.")
    os.environ["AWS_SECRET_ACCESS_KEY"] = secretAccessKey
    print("Exported AWS_SECRET_ACCESS_KEY to environment variables.")


if __name__ == "__main__":
    print(splashMsg)
    accessKeyId, secretAccessKey = requestAndValidateCredentials()
    print()
    createCondorFiles(accessKeyId, secretAccessKey)
    exportCredToEnv(accessKeyId, secretAccessKey)
    print()
    print("You're all set up!")
