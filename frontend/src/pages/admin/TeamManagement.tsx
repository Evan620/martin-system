import { useState, useEffect } from 'react'
import { userService, UserUpdateData } from '../../services/userService'
import { User, UserRole } from '../../types/auth'
import { Card, Button, Badge, Avatar } from '../../components/ui'
import { toast } from 'react-toastify'

export default function TeamManagement() {
    const [users, setUsers] = useState<User[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        loadUsers()
    }, [])

    const loadUsers = async () => {
        setIsLoading(true)
        try {
            const data = await userService.getUsers()
            setUsers(data)
        } catch (error) {
            console.error('Failed to load users', error)
            toast.error('Failed to load users')
        } finally {
            setIsLoading(false)
        }
    }

    const handleUpdateUser = async (userId: string, data: UserUpdateData) => {
        try {
            await userService.updateUser(userId, data)
            toast.success('User updated successfully')
            loadUsers()
        } catch (error) {
            console.error('Failed to update user', error)
            toast.error('Failed to update user')
        }
    }

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm('Are you sure you want to delete this user?')) return
        try {
            await userService.deleteUser(userId)
            toast.success('User deleted successfully')
            loadUsers()
        } catch (error) {
            console.error('Failed to delete user', error)
            toast.error('Failed to delete user')
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold">Team Management</h1>
            </div>

            <Card className="overflow-hidden border-slate-800 bg-slate-900/50">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-slate-800/50 border-b border-slate-800">
                                <th className="px-6 py-4 text-sm font-semibold text-slate-300">User</th>
                                <th className="px-6 py-4 text-sm font-semibold text-slate-300">Role</th>
                                <th className="px-6 py-4 text-sm font-semibold text-slate-300">Status</th>
                                <th className="px-6 py-4 text-sm font-semibold text-slate-300 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {users.map((user) => (
                                <tr key={user.id} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <Avatar alt={user.full_name} size="sm" />
                                            <div>
                                                <div className="font-medium text-white">{user.full_name}</div>
                                                <div className="text-xs text-slate-400">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <select
                                            className="bg-slate-800 border-slate-700 text-sm rounded-md px-2 py-1 focus:ring-blue-500"
                                            value={user.role}
                                            onChange={(e) => handleUpdateUser(user.id, { role: e.target.value as UserRole })}
                                        >
                                            {Object.values(UserRole).map((role) => (
                                                <option key={role} value={role}>
                                                    {role.replace('_', ' ').toUpperCase()}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="px-6 py-4">
                                        <Badge variant={user.is_active ? 'success' : 'warning'}>
                                            {user.is_active ? 'Active' : 'Inactive'}
                                        </Badge>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex justify-end gap-2">
                                            <Button
                                                size="sm"
                                                variant={user.is_active ? 'outline' : 'primary'}
                                                onClick={() => handleUpdateUser(user.id, { is_active: !user.is_active })}
                                            >
                                                {user.is_active ? 'Deactivate' : 'Activate'}
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="danger"
                                                onClick={() => handleDeleteUser(user.id)}
                                            >
                                                Delete
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>
        </div>
    )
}
