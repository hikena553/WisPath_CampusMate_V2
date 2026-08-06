from app.models.user import User, UserRole
from app.models.campus import CampusFigure, CampusScenery
from app.models.academic import College, Major, ClassGroup, Course, Grade, Exam
from app.models.growth import GrowthRecord
from app.models.service import ServiceTicket
from app.models.knowledge import KnowledgeItem
from app.models.leave import LeaveRequest
from app.models.crisis import AIDialogSummary
from app.models.certificate import Certificate
from app.models.conversation import Conversation, ConversationMessage
from app.models.message import Message
from app.models.announcement import TeacherAnnouncement, AnnouncementRead, TeacherSchedule
from app.models.document import Document, DocumentChunk
from app.models.notification import Notification, NotificationType
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.models.setting import SystemSetting
from app.models.profile import StudentProfileSnapshot, ConversationSummary
