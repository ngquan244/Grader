import React, { useState, useCallback } from 'react';
import { uploadApi } from '../api/upload';
import { Upload, Image, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const UploadPanel: React.FC = () => {
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [imageResult, setImageResult] = useState<{ success: boolean; message: string } | null>(null);
  const [pdfResult, setPdfResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleImageDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith('image/')
    );
    setImageFiles((prev) => [...prev, ...files]);
    setImageResult(null);
  }, []);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setImageFiles((prev) => [...prev, ...files]);
      setImageResult(null);
    }
  };

  const handlePdfSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setPdfFile(e.target.files[0]);
      setPdfResult(null);
    }
  };

  const uploadImages = async () => {
    if (imageFiles.length === 0) return;
    
    setUploadingImages(true);
    try {
      const dt = new DataTransfer();
      imageFiles.forEach((f) => dt.items.add(f));
      const result = await uploadApi.uploadImages(dt.files);
      setImageResult({ success: result.success, message: result.message });
      if (result.success) {
        setImageFiles([]);
      }
    } catch (error) {
      setImageResult({ success: false, message: 'Lỗi khi upload ảnh' });
    } finally {
      setUploadingImages(false);
    }
  };

  const uploadPdf = async () => {
    if (!pdfFile) return;
    
    setUploadingPdf(true);
    try {
      const result = await uploadApi.uploadPdf(pdfFile);
      setPdfResult({ success: result.success, message: result.message });
      if (result.success) {
        setPdfFile(null);
      }
    } catch (error) {
      setPdfResult({ success: false, message: 'Lỗi khi upload PDF' });
    } finally {
      setUploadingPdf(false);
    }
  };

  const removeImage = (index: number) => {
    setImageFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="upload-panel">
      <h2>Upload Files</h2>

      {/* Image Upload Section */}
      <div className="upload-section">
        <h3>
          <Image size={20} />
          Upload ảnh bài thi
        </h3>
        <p className="upload-hint">Ảnh sẽ được lưu vào thư mục kaggle/Filled-temp/</p>

        <div
          className="drop-zone"
          onDrop={handleImageDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          <Upload size={40} />
          <p>Kéo thả ảnh vào đây hoặc click để chọn</p>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageSelect}
          />
        </div>

        {imageFiles.length > 0 && (
          <div className="file-list">
            <h4>Đã chọn {imageFiles.length} ảnh:</h4>
            <ul>
              {imageFiles.map((file, index) => (
                <li key={index}>
                  <span>{file.name}</span>
                  <button onClick={() => removeImage(index)}>
                    <XCircle size={16} />
                  </button>
                </li>
              ))}
            </ul>
            <button
              className="btn-primary"
              onClick={uploadImages}
              disabled={uploadingImages}
            >
              {uploadingImages ? (
                <>
                  <Loader2 className="spin" size={18} />
                  Đang upload...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload {imageFiles.length} ảnh
                </>
              )}
            </button>
          </div>
        )}

        {imageResult && (
          <div className={`result-message ${imageResult.success ? 'success' : 'error'}`}>
            {imageResult.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
            {imageResult.message}
          </div>
        )}
      </div>

      {/* PDF Upload Section */}
      <div className="upload-section">
        <h3>
          <FileText size={20} />
          Upload PDF đề thi
        </h3>
        <p className="upload-hint">PDF sẽ được sử dụng để tạo quiz</p>

        <div className="drop-zone">
          <Upload size={40} />
          <p>Chọn file PDF đề thi</p>
          <input type="file" accept=".pdf" onChange={handlePdfSelect} />
        </div>

        {pdfFile && (
          <div className="file-list">
            <h4>Đã chọn:</h4>
            <ul>
              <li>
                <FileText size={16} />
                <span>{pdfFile.name}</span>
                <button onClick={() => setPdfFile(null)}>
                  <XCircle size={16} />
                </button>
              </li>
            </ul>
            <button
              className="btn-primary"
              onClick={uploadPdf}
              disabled={uploadingPdf}
            >
              {uploadingPdf ? (
                <>
                  <Loader2 className="spin" size={18} />
                  Đang upload...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload PDF
                </>
              )}
            </button>
          </div>
        )}

        {pdfResult && (
          <div className={`result-message ${pdfResult.success ? 'success' : 'error'}`}>
            {pdfResult.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
            {pdfResult.message}
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadPanel;
