from app.models.user import User, UserRole
from app.models.campus import CampusScenery, CampusImpressionItem
from app.models.academic import College, Major, ClassGroup, Course, Semester, Grade, Exam
from app.models.growth import GrowthRecord
from app.models.service import ServiceTicket
from app.models.knowledge import KnowledgeItem
from app.models.leave import LeaveRequest
from app.models.crisis import AIDialogSummary
from app.models.certificate import Certificate
from app.models.conversation import Conversation, ConversationMessage
from app.models.message import Message
from app.models.group import Group, GroupMember, GroupMessage
from app.models.announcement import TeacherAnnouncement, AnnouncementRead, TeacherSchedule
from app.models.document import Document, DocumentChunk
from app.models.notification import Notification, NotificationType
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.models.setting import SystemSetting
from app.models.profile import StudentProfileSnapshot, ConversationSummary
from app.models.lost_found import LostFoundItem, LostFoundComment
from app.models.plan import GrowthGoal, StudyPlan, PlanTask, PlanCheckin, PlanStage
from app.models.community import CommunityPost, CommunityComment, CommunityLike
from app.models.portfolio import StudentResume
from app.models.favorite import ResourceFavorite
from app.models.emotion import EmotionRecord
from app.models.material import MaterialArchive
from app.models.sms import SmsLog
from app.models.feed import FeedSource, ExternalFeedItem
from app.models.teacher_task import TeacherTask, TaskSourceType, TaskStatus
from app.models.care_record import CareRecord, CareRecordType
from app.models.teacher_portfolio import (
    PortfolioItemType,
    PortfolioVisibility,
    TeacherPortfolioItem,
)
from app.models.peer_survey import (
    PeerSurvey,
    PeerSurveyResponse,
    PeerSurveyStatus,
    PeerSurveyTargetType,
)
from app.models.care_center import (
    CareEvent,
    CareEventType,
    HomeVisitMethod,
    HomeVisitRecord,
    PraiseRecord,
    PraiseType,
)
from app.models.guardian import (
    Guardian,
    GuardianChannel,
    GuardianContactLog,
    GuardianContactStatus,
    GuardianScene,
    GuardianShareLink,
)
from app.models.learning_event import LearningEvent
from app.models.workflow import WorkflowDef, WorkflowInstance, WorkflowStatus
