import json

import frappe
from openai import AssistantEventHandler
from openai.types.beta.threads import Text
from openai.types.beta.threads.runs import RunStep
from typing_extensions import override

from raven.ai.functions import delete_document, delete_documents, get_document, get_documents
from raven.ai.openai_client import get_open_ai_client


def stream_response(ai_thread_id: str, bot, channel_id: str):

	client = get_open_ai_client()

	assistant_id = bot.openai_assistant_id

	class EventHandler(AssistantEventHandler):
		@override
		def on_run_step_done(self, run_step: RunStep) -> None:
			details = run_step.step_details
			if details.type == "tool_calls":
				for tool in details.tool_calls:
					if tool.type == "code_interpreter":
						self.publish_event("Running code...")
					if tool.type == "file_search":
						self.publish_event("Searching file contents...")
			else:
				self.publish_event("Raven AI is thinking...")

		@override
		def on_text_done(self, text: Text):
			bot.send_message(channel_id=channel_id, text=text.value)

			frappe.publish_realtime(
				"ai_event_clear",
				{
					"channel_id": channel_id,
				},
				doctype="Raven Channel",
				docname=channel_id,
				after_commit=True,
			)

		@override
		def on_event(self, event):
			# Retrieve events that are denoted with 'requires_action'
			# since these will have our tool_calls
			if event.event == "thread.run.requires_action":
				run_id = event.data.id  # Retrieve the run ID from the event data
				self.handle_requires_action(event.data, run_id)

		def publish_event(self, text):
			frappe.publish_realtime(
				"ai_event",
				{
					"text": text,
					"channel_id": channel_id,
					"bot": bot.name,
				},
				doctype="Raven Channel",
				docname=channel_id,
			)

		def handle_requires_action(self, data, run_id):
			tool_outputs = []

			for tool in data.required_action.submit_tool_outputs.tool_calls:

				function = None

				try:
					function = frappe.get_cached_doc("Raven AI Function", tool.function.name)
				except frappe.DoesNotExistError:
					tool_outputs.append({"tool_call_id": tool.id, "output": "Function not found"})
					return

				# When calling the function, we need to pass the arguments as named params/json
				# Args is a dictionary of the form {"param_name": "param_value"}

				try:
					args = json.loads(tool.function.arguments)

					# Check the type of function and then call it accordingly

					function_output = {}

					if function.type == "Custom Function":
						function_name = frappe.get_attr(function.function_path)

						if bot.allow_bot_to_write_documents:
							# We can commit to the database if writes are allowed
							if function.pass_parameters_as_json:
								function_output = function_name(args)
							else:
								function_output = function_name(**args)
						else:
							# We need to savepoint and then rollback
							frappe.db.savepoint(run_id + "_" + tool.id)
							if function.pass_parameters_as_json:
								function_output = function_name(args)
							else:
								function_output = function_name(**args)
							frappe.db.rollback(save_point=run_id + "_" + tool.id)

					if function.type == "Get Document":
						self.publish_event(
							"Fetching {} {}...".format(function.reference_doctype, args.get("document_id"))
						)
						function_output = get_document(function.reference_doctype, **args)

					if function.type == "Get Multiple Documents":
						self.publish_event(f"Fetching multiple {function.reference_doctype}s...")
						function_output = get_documents(function.reference_doctype, **args)

					if function.type == "Delete Document":
						self.publish_event(
							"Deleting {} {}...".format(function.reference_doctype, args.get("document_id"))
						)
						function_output = delete_document(function.reference_doctype, **args)

					if function.type == "Delete Multiple Documents":
						self.publish_event(f"Deleting multiple {function.reference_doctype}s...")
						function_output = delete_documents(function.reference_doctype, **args)

					tool_outputs.append(
						{"tool_call_id": tool.id, "output": json.dumps(function_output, default=str)}
					)
				except Exception as e:
					tool_outputs.append(
						{
							"tool_call_id": tool.id,
							"output": json.dumps(
								{
									"message": "There was an error in the function call",
									"error": str(e),
								},
								default=str,
							),
						}
					)

			# Submit all tool_outputs at the same time
			self.submit_tool_outputs(tool_outputs, run_id)

		def submit_tool_outputs(self, tool_outputs, run_id):
			# Use the submit_tool_outputs_stream helper
			with client.beta.threads.runs.submit_tool_outputs_stream(
				thread_id=self.current_run.thread_id,
				run_id=self.current_run.id,
				tool_outputs=tool_outputs,
				event_handler=EventHandler(),
			) as stream:
				self.publish_event("Raven AI is thinking...")
				for text in stream.text_deltas:
					print(text, end="", flush=True)
				print()

	# We need to get the instructions from the bot
	instructions = get_instructions(bot)
	with client.beta.threads.runs.stream(
		thread_id=ai_thread_id,
		assistant_id=assistant_id,
		event_handler=EventHandler(),
		instructions=instructions,
	) as stream:
		stream.until_done()


def get_instructions(bot):

	# If no instruction is set, or dynamic instruction is disabled, we return None
	if not bot.instruction or not bot.dynamic_instructions:
		return None

	vars = get_variables_for_instructions(bot)

	instructions = frappe.render_template(bot.instruction, vars)
	return instructions


def get_variables_for_instructions(bot):
	return {
		"user_first_name": "Nikhil",
		"company": "The Commit Company (Demo)",
		"employee_id": "HR-EMP-00001",
		"department": "Product - TCCD",
	}
