import React from 'react';

const FileDropZone = ({ dragging, uploading, onDrop, onDragOver, onDragLeave, onClick }) => {
  return (
    <div
      id='file-drop-zone'
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={onClick}
      className={`
        w-full p-8 mt-3 text-center cursor-pointer rounded-lg
        transition-all duration-300 ease-in-out
        ${dragging 
          ? 'border-2 border-dashed border-white bg-opacity-10 bg-white' 
          : 'border-2 border-solid border-white bg-transparent'}
        ${uploading 
          ? 'bg-opacity-10 bg-white' 
          : 'hover:bg-opacity-5 hover:bg-white'}
      `}
    >
      {uploading ? (
        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="animate-pulse text-white">Uploading...</div>
          <div className="text-sm text-gray-300">Please wait while we process your file</div>
        </div>
      ) : dragging ? (
        <div className="text-white font-medium">Drop the PDF or Word file here...</div>
      ) : (
        <div className="text-gray-300">
          Drag and drop a PDF or Word file here, or click to select a file
        </div>
      )}
        </div>
    );
};

export default FileDropZone;