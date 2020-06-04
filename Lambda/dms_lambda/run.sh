sam package --template-file template.yaml --s3-bucket 20200602-sambucket --output-template-file packaged.yaml


sam deploy --template-file ./packaged.yaml --stack-name mySAMstack --capabilities CAPABILITY_IAM