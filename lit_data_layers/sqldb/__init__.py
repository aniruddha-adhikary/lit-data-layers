import datetime
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from chainlit import PersistedUser, User, ThreadDict
from chainlit.data import BaseDataLayer, queue_until_user_message
from chainlit.element import ElementDict
from chainlit.step import StepDict
from chainlit.types import Feedback, Pagination, ThreadFilter
from literalai import PageInfo
from literalai import PaginatedResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, selectinload

from .models import Base, PersistedUserModel, ElementModel, ThreadModel, StepModel, Feedback as FeedbackModel


class SqlDataLayer(BaseDataLayer):
    def __init__(self):
        self.database_url = os.environ.get('LIT_DATABASE_URL')

        if not self.database_url:
            raise EnvironmentError('LIT_DATABASE_URL is not defined in the environment.')

        self.engine = create_async_engine(self.database_url, echo=True)
        self.AsyncSession = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def initialize_database(self):
        """
        Asynchronously create database tables if they do not exist.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def async_context(self):
        """
        Provide an asynchronous context manager for database sessions.
        This ensures that the session is properly closed after use.
        """
        async with self.AsyncSession() as session:
            return session.begin

    async def get_user(self, identifier: str, no_create=False) -> Optional["PersistedUser"]:
        """
        Retrieve a user by their identifier.

        :param identifier: The unique identifier of the user.
        :return: An instance of PersistedUser if found, otherwise None.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(PersistedUserModel).where(PersistedUserModel.identifier == identifier)
            )

            user_model = result.scalars().first()

            if user_model:
                return PersistedUser(
                    id=user_model.id,
                    identifier=user_model.identifier,
                    createdAt=str(user_model.createdAt),
                    metadata=user_model.metadata_ or {}
                )

        if not no_create:
            await self.create_user(
                user=User(identifier=identifier)
            )

            return self.get_user(identifier, no_create=True)
        else:
            return None

    async def create_user(self, user: "User") -> Optional["PersistedUser"]:
        """
        Create a new user or update an existing user's metadata.

        :param user: An instance of User containing the user's details.
        :return: An instance of PersistedUser with the created or updated user's details.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(PersistedUserModel).where(PersistedUserModel.identifier == user.identifier)
            )
            user_model = result.scalars().first()
            if user_model:
                user_model.metadata_ = user.metadata
            else:
                user_model = PersistedUserModel(
                    id=str(uuid.uuid4()),
                    identifier=user.identifier,
                    createdAt=datetime.now(timezone.utc),
                    metadata=user.metadata
                )
                session.add(user_model)
            await session.commit()

            return PersistedUser(
                id=user_model.id,
                identifier=user_model.identifier,
                createdAt=str(user_model.createdAt),
                metadata=user_model.metadata_
            )

    async def delete_user_session(self, id: str) -> bool:
        """
        Delete a user session by its ID.

        :param id: The ID of the user session to delete.
        :return: True if the session was successfully deleted, False otherwise.
        """
        return await super().delete_user_session(id)

    async def upsert_feedback(self, feedback: Feedback) -> str:
        """
        Insert or update feedback for a step.

        :param feedback: An instance of Feedback containing the feedback details.
        :return: The ID of the inserted or updated feedback.
        """
        if feedback.id:
            async with self.AsyncSession() as session:
                await session.execute(
                    update(FeedbackModel).
                    where(FeedbackModel.id == feedback.id).
                    values(
                        comment=feedback.comment,
                        value=str(feedback.value)
                    )
                )
                await session.commit()
            return feedback.id
        else:
            async with self.AsyncSession() as session:
                new_feedback = FeedbackModel(
                    for_id=feedback.forId,
                    value=str(feedback.value),
                    comment=feedback.comment,
                )
                session.add(new_feedback)
                await session.commit()
                return str(new_feedback.id)

    @queue_until_user_message()
    async def create_element(self, element_dict: "ElementDict") -> "ElementDict":
        """
        Create a new element and persist it to the database.

        :param element_dict: A dictionary containing the element's details.
        :return: A dictionary with the created element's details.
        """
        async with self.AsyncSession() as session:
            new_element = ElementModel(
                id=element_dict["id"],
                thread_id=element_dict["threadId"],
                type=element_dict["type"],
                chainlit_key=element_dict.get("chainlitKey"),
                url=element_dict.get("url"),
                object_key=element_dict.get("objectKey"),
                name=element_dict["name"],
                display=element_dict["display"],
                size=element_dict.get("size"),
                language=element_dict.get("language"),
                mime=element_dict.get("mime"),
                for_id=element_dict.get("forId"),
                page=element_dict.get("page"),
            )
            session.add(new_element)
            await session.commit()

            return {
                "id": new_element.id,
                "threadId": new_element.thread_id,
                "type": new_element.type,
                "chainlitKey": new_element.chainlit_key,
                "url": new_element.url,
                "objectKey": new_element.object_key,
                "name": new_element.name,
                "display": new_element.display,
                "size": new_element.size,
                "language": new_element.language,
                "mime": new_element.mime,
                "forId": new_element.for_id,
                "page": new_element.page,
            }

    async def get_element(self, thread_id: str, element_id: str) -> Optional["ElementDict"]:
        """
        Retrieve an element by its ID and associated thread ID.

        :param thread_id: The ID of the thread associated with the element.
        :param element_id: The ID of the element to retrieve.
        :return: A dictionary with the element's details if found, otherwise None.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(ElementModel).where(
                    ElementModel.thread_id == thread_id,
                    ElementModel.id == element_id
                )
            )
            element = result.scalars().first()
            if element:
                return {
                    "id": element.id,
                    "threadId": element.thread_id,
                    "type": element.type,
                    "chainlitKey": element.chainlit_key,
                    "url": element.url,
                    "objectKey": element.object_key,
                    "name": element.name,
                    "display": element.display,
                    "size": element.size,
                    "language": element.language,
                    "mime": element.mime,
                    "forId": element.for_id,
                    "page": element.page,
                }
            return None

    @queue_until_user_message()
    async def delete_element(self, element_id: str) -> bool:
        """
        Delete an element by its ID.

        :param element_id: The ID of the element to delete.
        :return: True if the element was successfully deleted, False otherwise.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(ElementModel).where(ElementModel.id == element_id)
            )
            element = result.scalars().first()
            if element:
                await session.delete(element)
                await session.commit()
                return True
            return False

    @queue_until_user_message()
    async def create_step(self, step_dict: "StepDict") -> "StepDict":
        """
        Create a new step and persist it to the database.

        :param step_dict: A dictionary containing the step's details.
        :return: A dictionary with the created step's details.
        """
        async with self.AsyncSession() as session:
            new_step = StepModel(
                id=step_dict["id"],
                thread_id=step_dict["threadId"],
                parent_id=step_dict.get("parentId"),
                name=step_dict["name"],
                type=step_dict["type"],
                input=step_dict.get("input"),
                output=step_dict.get("output"),
                metadata_=step_dict.get("metadata"),
                created_at=datetime.now(timezone.utc),
                start_time=datetime.now(timezone.utc),
                end_time=None,
            )
            session.add(new_step)
            await session.commit()

            return {
                "id": new_step.id,
                "threadId": new_step.thread_id,
                "name": new_step.name,
                "type": new_step.type,
                "input": new_step.input,
                "output": new_step.output,
                "metadata": new_step.metadata_,
                "createdAt": date_serialize(new_step.created_at),
                "start": date_serialize(new_step.start_time),
                "end": date_serialize(new_step.end_time),
            }

    @queue_until_user_message()
    async def update_step(self, step_dict: "StepDict") -> "StepDict":
        """
        Update an existing step's details in the database.

        :param step_dict: A dictionary containing the updated step's details.
        :return: A dictionary with the updated step's details.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(StepModel).where(StepModel.id == step_dict["id"])
            )
            step = result.scalars().first()
            if step:
                step.name = step_dict["name"]
                step.type = step_dict["type"]
                step.input = step_dict.get("input")
                step.output = step_dict.get("output")
                step.metadata_ = step_dict.get("metadata")
                step.created_at = datetime.fromisoformat(
                    step_dict.get("createdAt").replace("Z", "+00:00")) if step_dict.get(
                    "createdAt") else step.created_at
                step.start_time = datetime.fromisoformat(
                    step_dict.get("start").replace("Z", "+00:00")) if step_dict.get("start") else step.start_time
                step.end_time = datetime.fromisoformat(step_dict.get("end").replace("Z", "+00:00")) if step_dict.get(
                    "end") else step.end_time
                await session.commit()

                return {
                    "id": step.id,
                    "threadId": step.thread_id,
                    "name": step.name,
                    "type": step.type,
                    "input": step.input,
                    "output": step.output,
                    "metadata": step.metadata_,
                    "createdAt": date_serialize(step.created_at),
                    "start": date_serialize(step.start_time),
                    "end": date_serialize(step.end_time),
                }
            else:
                raise ValueError(f"Step with ID {step_dict['id']} not found")

    @queue_until_user_message()
    async def delete_step(self, step_id: str) -> bool:
        """
        Delete a step by its ID.

        :param step_id: The ID of the step to delete.
        :return: True if the step was successfully deleted, False otherwise.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(StepModel).where(StepModel.id == step_id)
            )
            step = result.scalars().first()
            if step:
                await session.delete(step)
                await session.commit()
                return True
            return False

    async def get_thread(self, thread_id: str) -> "Optional[ThreadDict]":
        """
        Retrieve a thread by its ID, including its associated steps and elements.

        :param thread_id: The ID of the thread to retrieve.
        :return: A dictionary with the thread's details if found, otherwise None.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )
            thread_model = result.scalars().first()
            if thread_model:
                # Retrieve steps for the thread
                steps_result = await session.execute(
                    select(StepModel).where(StepModel.thread_id == thread_id)
                )
                steps = steps_result.scalars().all()

                # Retrieve elements for the thread
                elements_result = await session.execute(
                    select(ElementModel).where(ElementModel.thread_id == thread_id)
                )
                elements = elements_result.scalars().all()

                # Retrieve user for the thread
                user_result = await session.execute(
                    select(PersistedUserModel).where(PersistedUserModel.id == thread_model.user_id)
                )
                user_model = user_result.scalars().first()
                user_dict = {
                    "id": user_model.id,
                    "identifier": user_model.identifier,
                    "createdAt": user_model.createdAt.isoformat() if thread_model.createdAt else None,
                    "metadata": user_model.metadata_
                } if user_model else None

                return {
                    "id": thread_model.id,
                    "name": thread_model.name,
                    "createdAt": date_serialize(thread_model.createdAt),
                    "metadata": thread_model.metadata_,
                    "tags": thread_model.tags,
                    "user": user_dict,
                    "steps": [{
                        "id": step.id,
                        "threadId": step.thread_id,
                        "parentId": step.parent_id,
                        "name": step.name,
                        "type": step.type,
                        "input": step.input,
                        "output": step.output,
                        "metadata": step.metadata_,
                        "createdAt": date_serialize(step.created_at),
                        "start": date_serialize(step.start_time),
                        "end": date_serialize(step.end_time),
                    } for step in steps],
                    "elements": [{
                        "id": element.id,
                        "threadId": element.thread_id,
                        "type": element.type,
                        "chainlitKey": element.chainlit_key,
                        "url": element.url,
                        "objectKey": element.object_key,
                        "name": element.name,
                        "display": element.display,
                        "size": element.size,
                        "language": element.language,
                        "mime": element.mime,
                        "forId": element.for_id,
                        "page": element.page,
                    } for element in elements],
                }
            return None

    async def get_thread_author(self, thread_id: str) -> str:
        """
        Retrieve the identifier of the author of a thread.

        :param thread_id: The ID of the thread.
        :return: The identifier of the thread's author.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(PersistedUserModel.identifier).join(ThreadModel).where(ThreadModel.id == thread_id)
            )
            user_identifier = result.scalars().first()
            return user_identifier if user_identifier else ""

    async def delete_thread(self, thread_id: str):
        """
        Delete a thread by its ID.

        :param thread_id: The ID of the thread to delete.
        :return: True if the thread was successfully deleted, False otherwise.
        """
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )
            thread = result.scalars().first()
            if thread:
                await session.delete(thread)
                await session.commit()
                return True
            return False

    async def list_threads(self, pagination: "Pagination", filters: "ThreadFilter") -> "PaginatedResponse[ThreadDict]":
        """
        List threads based on pagination and filter criteria.

        :param pagination: An instance of Pagination containing pagination details.
        :param filters: An instance of ThreadFilter containing filter criteria.
        :return: A PaginatedResponse containing a list of threads and page information.
        """
        async with self.AsyncSession() as session:
            query = select(ThreadModel).options(selectinload(ThreadModel.user)).join(PersistedUserModel)
            if filters.userId:
                query = query.where(PersistedUserModel.id == filters.userId)
            if filters.search:
                query = query.where(ThreadModel.name.ilike(f'%{filters.search}%'))
            if filters.feedback is not None:
                # Assuming there is a FeedbackModel with a thread_id and value fields
                query = query.join(FeedbackModel).where(FeedbackModel.value == filters.feedback)

            query = query.order_by(ThreadModel.createdAt.desc())
            if pagination.cursor:
                query = query.where(ThreadModel.id > pagination.cursor)
            query = query.limit(pagination.first)

            result = await session.execute(query)
            threads = result.scalars().all()

            # Convert ThreadModel instances to ThreadDict
            threads_data = []
            for thread in threads:
                # Explicitly load steps for the thread
                steps_result = await session.execute(
                    select(StepModel).where(StepModel.thread_id == thread.id)
                )
                steps = steps_result.scalars().all()

                # Explicitly load elements for the thread
                elements_result = await session.execute(
                    select(ElementModel).where(ElementModel.thread_id == thread.id)
                )
                elements = elements_result.scalars().all()

                threads_data.append({
                    "id": thread.id,
                    "name": thread.name,
                    "createdAt": date_serialize(thread.createdAt),
                    "metadata": thread.metadata_,
                    "tags": thread.tags,
                    "user": {
                        "id": thread.user.id,
                        "identifier": thread.user.identifier,
                        "createdAt": date_serialize(thread.user.createdAt),
                        "metadata": thread.user.metadata_
                    },
                    "steps": [{
                        "id": step.id,
                        "threadId": step.thread_id,
                        "name": step.name,
                        "type": step.type,
                        "input": step.input,
                        "output": step.output,
                        "metadata": step.metadata_,
                        "createdAt": date_serialize(step.created_at),
                        "start": date_serialize(step.start_time),
                        "end": date_serialize(step.end_time),
                    } for step in steps],
                    "elements": [{
                        "id": element.id,
                        "threadId": element.thread_id,
                        "type": element.type,
                        "chainlitKey": element.chainlit_key,
                        "url": element.url,
                        "objectKey": element.object_key,
                        "name": element.name,
                        "display": element.display,
                        "size": element.size,
                        "language": element.language,
                        "mime": element.mime,
                        "forId": element.for_id,
                        "page": element.page,
                    } for element in elements],
                })

            page_info = PageInfo(
                hasNextPage=len(threads) == pagination.first,
                startCursor=threads[0].id if threads else None,
                endCursor=threads[-1].id if threads else None
            ).to_dict()

            response = PaginatedResponse(data=threads_data, pageInfo=page_info)
            return response

    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None,
                            metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """
        Update a thread's details in the database.

        :param thread_id: The ID of the thread to update.
        :param name: The new name of the thread, if provided.
        :param user_id: The new user ID associated with the thread, if provided.
        :param metadata: The new metadata for the thread, if provided.
        :param tags: The new list of tags for the thread, if provided.
        """
        print('update_thread', thread_id, name, user_id, metadata, tags)
        async with self.AsyncSession() as session:
            result = await session.execute(
                select(ThreadModel).where(ThreadModel.id == thread_id)
            )
            thread = result.scalars().first()
            if not thread:
                thread = ThreadModel(
                    id=thread_id,
                    name=name,
                    createdAt=datetime.now(timezone.utc)
                )

            if name is not None:
                thread.name = name
            if user_id is not None:
                thread.user_id = user_id
            if metadata is not None:
                thread.metadata_ = metadata
            if tags is not None:
                thread.tags = tags

            session.add(thread)
            await session.commit()


def date_serialize(date: datetime) -> str:
    if date is None:
        return None

    return date.isoformat()
