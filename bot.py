from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import ChannelAccount
import logging
from openai import AzureOpenAI
from datetime import datetime
import time
import json
import re
from config import DefaultConfig

CONFIG = DefaultConfig()

class MyBot(ActivityHandler):
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=CONFIG.OPENAI_API_KEY,
            api_version="2024-05-01-preview",
            azure_endpoint=CONFIG.OPENAI_ENDPOINT
        )
        self.assistant_id = "asst_erDke1GNaDMMC6dvlFrNeCL2"
        self.conversation_threads = {}

    def handle_vote_and_decision(self, prompt, conversation_id):
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt_with_datetime = f"Current date and time: {current_datetime}\n\n{prompt}"

        try:
            if conversation_id in self.conversation_threads:
                thread_id = self.conversation_threads[conversation_id]
                logging.info("Using existing Thread ID: %s for Conversation ID: %s", thread_id, conversation_id)
            else:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
                self.conversation_threads[conversation_id] = thread_id
                logging.info("New Thread Created: %s for Conversation ID: %s", thread_id, conversation_id)

            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt_with_datetime
            )
            logging.info("User Message Added: %s", message)

            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )

            start_time = time.time()
            status = run.status

            while status not in ["completed", "cancelled", "expired", "failed"]:
                time.sleep(5)
                run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                elapsed_time = time.time() - start_time
                logging.info("Elapsed time: %d minutes %d seconds", int(elapsed_time // 60), int(elapsed_time % 60))
                status = run.status
                logging.info('Run Status: %s', status)

            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            logging.info("Thread Messages after run completion: %s", messages.model_dump_json(indent=2))

            data = json.loads(messages.model_dump_json(indent=2))
            response = data['data'][0]['content'][0]['text']['value']

            response = re.sub(r"【\d+:\d+†.*?】", "", response)
            response = re.sub(r"【\d+†.*?】", "", response)

            logging.info("Final Response: %s", response)
            return response, thread_id
        except Exception as e:
            logging.error(f"Error in handle_vote_and_decision: {e}")
            raise

    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text
        conversation_id = turn_context.activity.conversation.id

        try:
            decision_response, thread_id = self.handle_vote_and_decision(user_input, conversation_id)
            await turn_context.send_activity(f"{decision_response}")
        except Exception as e:
            logging.error(f"Azure OpenAI API error: {e}")
            await turn_context.send_activity(
                "Sorry, I encountered an error while processing your request."
            )

    async def on_members_added_activity(
        self, members_added: ChannelAccount, turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(" مرحبا انا علي، عضو تنفيذي في اللجنة الوطنية للتخطيط في قطر. دوري هو تحليل المقترحات الاستراتيجية، تقييم تأثيرها طويل الأمد، واتخاذ قرارات مستنيرة بشأن المبادرات التي تشكل نمو وتطوير البلاد. كيف يمكنني مساعدتك اليوم؟")
