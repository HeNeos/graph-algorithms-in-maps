FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY modules ./modules/

ARG FUNCTION_NAME
COPY lambdas/${FUNCTION_NAME} ./lambdas/${FUNCTION_NAME}

ENV LAMBDA_HANDLER=lambdas.${FUNCTION_NAME}.lambda_function.lambda_handler

CMD ${LAMBDA_HANDLER}
