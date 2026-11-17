export function EstimateNotice({ count, className = '' }: { count: number; className?: string }) {
  return <p className={className}>
    {count} công việc tính tiến độ thiếu giờ ước lượng.
    {count > 0 && ' Các mục thiếu giờ dùng trọng số trung bình; nếu tất cả đều thiếu giờ thì dùng trọng số bằng nhau.'}
  </p>
}
