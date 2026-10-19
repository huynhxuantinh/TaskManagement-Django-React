import { Button } from '../../components/ui/Button'
import type { Project, User } from '../../types/api'
import { canManageProject } from './permissions'

export function ProjectActions({
  user,
  project,
  onEdit,
  onDelete,
}: {
  user: User
  project: Project
  onEdit: () => void
  onDelete: () => void
}) {
  if (!canManageProject(user, project)) return null
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="secondary" onClick={onEdit} aria-label={`Sửa dự án ${project.name}`}>
        Sửa
      </Button>
      <Button type="button" variant="ghost" onClick={onDelete} aria-label={`Xóa dự án ${project.name}`} className="!text-red-700">
        Xóa
      </Button>
    </div>
  )
}
