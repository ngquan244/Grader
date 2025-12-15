# Kaggle Directory

Chứa notebooks và data từ Kaggle competition.

## Structure

```
kaggle/
├── notebooks/           # Jupyter notebooks
│   └── *.ipynb         # Competition notebooks
├── data/               # Competition data
│   ├── train.csv
│   ├── test.csv
│   └── sample_submission.csv
└── README.md           # This file
```

## Usage

1. **Thêm notebook**: Kéo file `.ipynb` vào `notebooks/`
2. **Thêm data**: Kéo dataset vào `data/`
3. **Chạy notebook**: Agent sẽ execute notebook trực tiếp

## Notes

- Notebooks sẽ được execute trong môi trường Python hiện tại
- Dependencies cần thiết sẽ được cài tự động
- Output và results được lưu trong `kaggle/data/`
