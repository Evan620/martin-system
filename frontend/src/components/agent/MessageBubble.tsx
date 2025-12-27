import React from 'react';
import { ChatMessage, ChatMessageType, MessageAction } from '../../types/agent';

interface MessageBubbleProps {
  message: ChatMessage;
  onActionClick?: (action: MessageAction) => void;
  onFileUpload?: (files: File[]) => void;
}

/**
 * Rich Message Bubble Component
 *
 * Renders different message types with appropriate UI:
 * - Text messages with markdown formatting
 * - Tool execution status
 * - File attachments
 * - Action buttons
 * - Agent request forms
 */
export function MessageBubble({ message, onActionClick, onFileUpload }: MessageBubbleProps) {
  const isUser = message.sender === 'user';
  const isSystem = message.sender === 'system';

  const renderContent = () => {
    switch (message.message_type) {
      case ChatMessageType.TOOL_EXECUTION:
        return <ToolExecutionView tool_name={message.tool_name} status={message.tool_status} result={message.tool_result} />;

      case ChatMessageType.AGENT_REQUEST:
        return (
          <>
            <div className="mb-3">{message.content}</div>
            <AgentRequestForm message={message} onSubmit={onActionClick} onFileUpload={onFileUpload} />
          </>
        );

      case ChatMessageType.FILE_ATTACHMENT:
        return <FileAttachmentView attachments={message.attachments || []} />;

      case ChatMessageType.COMMAND_RESULT:
        return (
          <>
            <div className="mb-2 text-xs font-bold text-blue-400">Command Result</div>
            <div>{message.content}</div>
          </>
        );

      default:
        return <div className="whitespace-pre-wrap">{message.content}</div>;
    }
  };

  const renderActions = () => {
    if (!message.actions || message.actions.length === 0) return null;

    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {message.actions.map(action => (
          <ActionButton key={action.action_id} action={action} onClick={() => onActionClick?.(action)} />
        ))}
      </div>
    );
  };

  const renderTimestamp = () => {
    const time = new Date(message.timestamp).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
    return <div className="text-xs text-slate-500 mt-1">{time}</div>;
  };

  // System messages are centered and styled differently
  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="px-4 py-2 bg-slate-800/50 rounded-lg text-xs text-slate-400">
          {renderContent()}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-4 mb-6 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">person</span>
          </div>
        ) : (
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">smart_toy</span>
          </div>
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div className="max-w-[80%]">
          {/* Message bubble */}
          <div
            className={`rounded-2xl p-4 ${
              isUser
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800/50 text-white border border-slate-700'
            }`}
          >
            {renderContent()}
            {renderActions()}
          </div>

          {/* Timestamp */}
          <div className={isUser ? 'text-right' : ''}>
            {renderTimestamp()}
          </div>

          {/* Attachments */}
          {message.attachments && message.attachments.length > 0 && message.message_type !== ChatMessageType.FILE_ATTACHMENT && (
            <div className="mt-2">
              <FileAttachmentView attachments={message.attachments} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Sub-components

function ActionButton({ action, onClick }: { action: MessageAction; onClick: () => void }) {
  const styleClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-slate-700 hover:bg-slate-600 text-white',
    success: 'bg-green-600 hover:bg-green-700 text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white'
  };

  const buttonClass = styleClasses[action.style as keyof typeof styleClasses] || styleClasses.primary;

  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg font-semibold text-sm flex items-center gap-2 transition-colors ${buttonClass}`}
    >
      {action.icon && <span className="material-symbols-outlined text-[18px]">{action.icon}</span>}
      {action.label}
    </button>
  );
}

function ToolExecutionView({ tool_name, status, result }: { tool_name?: string; status?: string; result?: any }) {
  if (!tool_name) return null;

  const statusConfig = {
    running: {
      icon: 'progress_activity',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      text: 'Running...'
    },
    success: {
      icon: 'check_circle',
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      text: 'Completed'
    },
    error: {
      icon: 'error',
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
      text: 'Error'
    }
  };

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.running;

  return (
    <div className={`${config.bgColor} border border-current ${config.color} rounded-lg p-3`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="material-symbols-outlined text-[20px] animate-pulse">{config.icon}</span>
        <span className="font-bold text-sm">
          {tool_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
        </span>
        <span className="text-xs opacity-80">{config.text}</span>
      </div>
      {result && status === 'success' && (
        <div className="text-xs opacity-80 mt-1">
          {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
        </div>
      )}
    </div>
  );
}

function AgentRequestForm({ message, onSubmit, onFileUpload }: { message: ChatMessage; onSubmit?: (action: MessageAction) => void; onFileUpload?: (files: File[]) => void }) {
  const [selectedValue, setSelectedValue] = React.useState<any>(null);
  const [uploadedFiles, setUploadedFiles] = React.useState<File[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setUploadedFiles(files);
    }
  };

  const handleSubmit = () => {
    if (message.request_type === 'file_upload') {
      onFileUpload?.(uploadedFiles);
    } else if (message.request_type === 'selection' && selectedValue) {
      const action: MessageAction = {
        action_id: message.message_id,
        action_type: 'dropdown' as any,
        label: 'Submit',
        value: selectedValue
      };
      onSubmit?.(action);
    }
  };

  // Dropdown/Selection request
  if (message.request_type === 'selection' && message.request_schema?.options) {
    return (
      <div className="space-y-3">
        <select
          value={selectedValue || ''}
          onChange={(e) => setSelectedValue(e.target.value)}
          className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white"
        >
          <option value="">Select an option...</option>
          {message.request_schema.options.map((opt: any) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleSubmit}
          disabled={!selectedValue}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold text-sm transition-colors"
        >
          Submit
        </button>
      </div>
    );
  }

  // File upload request
  if (message.request_type === 'file_upload') {
    return (
      <div className="space-y-3">
        <div className="border-2 border-dashed border-slate-600 rounded-lg p-6 text-center">
          <input
            type="file"
            onChange={handleFileChange}
            className="hidden"
            id={`file-upload-${message.message_id}`}
            multiple
          />
          <label htmlFor={`file-upload-${message.message_id}`} className="cursor-pointer">
            <span className="material-symbols-outlined text-4xl text-slate-500 mb-2 block">upload_file</span>
            <p className="text-sm text-slate-400">Drop files here or click to upload</p>
            {message.request_schema?.accepted_formats && (
              <p className="text-xs text-slate-500 mt-1">
                Accepted: {message.request_schema.accepted_formats.join(', ')}
              </p>
            )}
          </label>
        </div>
        {uploadedFiles.length > 0 && (
          <div className="space-y-1">
            {uploadedFiles.map((file, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm text-slate-300">
                <span className="material-symbols-outlined text-[16px]">description</span>
                {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </div>
            ))}
          </div>
        )}
        <button
          onClick={handleSubmit}
          disabled={uploadedFiles.length === 0}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold text-sm transition-colors"
        >
          Upload
        </button>
      </div>
    );
  }

  return null;
}

function FileAttachmentView({ attachments }: { attachments: any[] }) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div className="space-y-2">
      {attachments.map((file, idx) => (
        <div key={idx} className="flex items-center gap-3 p-3 bg-slate-900 border border-slate-700 rounded-lg">
          <span className="material-symbols-outlined text-blue-400">description</span>
          <div className="flex-1">
            <div className="text-sm font-medium">{file.filename}</div>
            <div className="text-xs text-slate-500">
              {file.file_type} • {(file.file_size / 1024).toFixed(1)} KB
            </div>
          </div>
          {file.url && (
            <a
              href={file.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition-colors"
            >
              Open
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

export default MessageBubble;
