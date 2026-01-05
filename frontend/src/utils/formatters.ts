/**
 * Format date to Vietnamese locale
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('vi-VN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format timestamp string (YYYYMMDD_HHMMSS) to readable format
 */
export function formatTimestamp(timestamp: string): string {
  const match = timestamp.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  if (!match) return timestamp;
  
  const [, year, month, day, hour, minute] = match;
  return `${day}/${month}/${year} ${hour}:${minute}`;
}

/**
 * Format score with evaluation
 */
export function formatScore(score: number): { text: string; color: string; evaluation: string } {
  if (score >= 8.5) {
    return { text: score.toFixed(1), color: 'text-green-600', evaluation: 'Xuất sắc' };
  } else if (score >= 7.0) {
    return { text: score.toFixed(1), color: 'text-blue-600', evaluation: 'Tốt' };
  } else if (score >= 5.0) {
    return { text: score.toFixed(1), color: 'text-yellow-600', evaluation: 'Đạt' };
  } else {
    return { text: score.toFixed(1), color: 'text-red-600', evaluation: 'Chưa đạt' };
  }
}

/**
 * Format file size to human readable
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return `${text.slice(0, length)}...`;
}
