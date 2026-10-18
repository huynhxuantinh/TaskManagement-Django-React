import { StatePanel } from '../components/ui/StatePanel'

export function PlaceholderPage({ title, milestone }: { title: string; milestone: string }) {
  return (
    <div className="grid min-h-[65vh] place-items-center">
      <StatePanel
        eyebrow={`${milestone} / In progress`}
        title={title}
        description="Khung điều hướng và phân quyền đã sẵn sàng. Màn hình nghiệp vụ sẽ được nối vào API trong chặng tiếp theo."
      />
    </div>
  )
}

