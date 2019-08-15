#export DEPLOYMENT_BUCKET_NAME ?= movie-chatbot-resources-028626156119
#export CAMPAIGN_ARN ?= arn:aws:personalize:us-east-1:028626156119:campaign/DEMO-sims-campaign-20m

check-env:
ifndef DEPLOYMENT_BUCKET_NAME
	$(error DEPLOYMENT_BUCKET_NAME is undefined. Specify the bucket name that should be used to upload the lambda package )
endif
ifndef CAMPAIGN_ARN
	$(error CAMPAIGN_ARN is undefined. Specify the ARN of the Personalize campaign to call )
endif

init: ##=> Install OS deps, python3.6 and dev tools
	$(info [*] Creating bucket... ${DEPLOYMENT_BUCKET_NAME})
	aws s3 ls | grep "${DEPLOYMENT_BUCKET_NAME}" || aws s3 mb 's3://${DEPLOYMENT_BUCKET_NAME}'

build:
	sam build 

package: build check-env
	# Package Lambda function defined locally and upload to S3 as an artifact
	sam package \
			--output-template-file packaged.yaml \
			--s3-bucket ${DEPLOYMENT_BUCKET_NAME}

deploy: package
	# Deploy SAM template as a CloudFormation stack
	sam deploy \
			--template-file packaged.yaml \
			--stack-name movie-chatbot \
			--capabilities CAPABILITY_IAM \
			--parameter-overrides  "ASSETS_BUCKET=${DEPLOYMENT_BUCKET_NAME} CAMPAIGN_ARN=${CAMPAIGN_ARN}"

  
