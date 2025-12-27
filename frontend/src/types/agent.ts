/**
 * Enhanced chat message types for rich UI communication.
 *
 * This mirrors the backend chat_messages.py schema for type safety
 * in the frontend chat interface.
 */

export enum ChatMessageType {
  USER_TEXT = "user_text",
  AGENT_TEXT = "agent_text",
  AGENT_SUGGESTION = "agent_suggestion",
  AGENT_REQUEST = "agent_request",
  SYSTEM = "system",
  TOOL_EXECUTION = "tool_execution",
  FILE_ATTACHMENT = "file_attachment",
  COMMAND_RESULT = "command_result"
}

export enum ActionType {
  BUTTON = "button",
  FILE_UPLOAD = "file_upload",
  FORM_INPUT = "form_input",
  DROPDOWN = "dropdown",
  CONFIRM = "confirm"
}

export interface MessageAction {
  action_id: string;
  action_type: ActionType;
  label: string;
  value?: any;
  style?: "primary" | "secondary" | "success" | "danger";
  icon?: string;
  handler_endpoint?: string;
}

export interface FileAttachment {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  url?: string;
  thumbnail_url?: string;
}

export interface ChatMessage {
  message_id: string;
  conversation_id: string;
  message_type: ChatMessageType;
  content: string;
  sender: "user" | "agent" | "system";
  timestamp: string;

  // Rich content
  metadata?: Record<string, any>;
  actions?: MessageAction[];
  attachments?: FileAttachment[];

  // Suggestion-specific
  suggestion_type?: string;
  suggestion_data?: Record<string, any>;

  // Request-specific
  request_type?: string;
  request_schema?: Record<string, any>;

  // Tool execution
  tool_name?: string;
  tool_status?: "running" | "success" | "error";
  tool_result?: Record<string, any>;
}

export interface AgentSuggestion {
  suggestion_id: string;
  title: string;
  description: string;
  suggestion_type: string;
  priority: "high" | "medium" | "low";
  action_data: Record<string, any>;
  icon?: string;
  expires_at?: string;
  created_at: string;
}

export interface ToolExecution {
  execution_id: string;
  tool_name: string;
  status: "running" | "success" | "error";
  started_at: string;
  completed_at?: string;
  result?: Record<string, any>;
  error?: string;
}

// Request/Response types

export interface EnhancedChatRequest {
  message: string;
  conversation_id?: string;
  twg_id?: string;
  attachments?: Array<Record<string, any>>;
}

export interface EnhancedChatResponse {
  message: ChatMessage;
  suggestions: AgentSuggestion[];
  tool_executions: ToolExecution[];
  conversation_id: string;
}

export interface SuggestionAcceptRequest {
  suggestion_id: string;
}

export interface AgentRequestResponse {
  request_id: string;
  response_data: Record<string, any>;
}

// Command system types

export interface CommandDefinition {
  command: string;
  description: string;
  examples: string[];
  parameters?: CommandParameter[];
  category?: string;
  icon?: string;
}

export interface CommandParameter {
  name: string;
  type: "string" | "number" | "date" | "file" | "select";
  required: boolean;
  description: string;
  options?: { label: string; value: string }[];
  default?: any;
}

export interface CommandAutocompleteResult {
  command: string;
  description: string;
  examples: string;
  category?: string;
  match_score?: number;
}

// Agent mention types

export interface AgentMention {
  agent_id: string;
  agent_name: string;
  icon?: string;
  description?: string;
}

// Conversation types

export interface Conversation {
  conversation_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}
