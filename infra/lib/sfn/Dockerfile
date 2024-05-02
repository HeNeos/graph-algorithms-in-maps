FROM public.ecr.aws/lambda/python:3.10

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY modules ./modules/

ARG FUNCTION_NAME=getGraph
COPY lambdas/${FUNCTION_NAME}/lambda_function.py ./lambdas/${FUNCTION_NAME}/lambda_function.py

ENV LAMBDA_HANDLER=lambdas.${FUNCTION_NAME}.lambda_function.lambda_handler

CMD ${LAMBDA_HANDLER}
